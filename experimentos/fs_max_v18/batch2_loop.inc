// A batch is always two logical SCP1 frames. Both are prepared under one
// output_lock; no producer wait is introduced for the second half.
static scope_batch2::Half prepare_batch_half(uint8_t *packet, uint32_t seq) {
    scope_wav::Reply wav_reply{};
    scope_control::Reply reply{};
    scope_acq::Reply config_reply{};
    scope_gen::Reply generator_reply{};
    const bool have_wav = k_msgq_get(&wav_replies,&wav_reply,K_NO_WAIT)==0;
    const bool have_generator = !have_wav && k_msgq_get(&generator_replies,&generator_reply,K_NO_WAIT)==0;
    const bool have_config = !have_wav && !have_generator && k_msgq_get(&settings_replies,&config_reply,K_NO_WAIT)==0;
    const bool have_reply = !have_wav && !have_generator && !have_config &&
        k_msgq_get(&control_replies,&reply,K_NO_WAIT)==0;
    const bool word=batch_dma_word;
    const bool pipelined=batch_dma_high;
    const bool have_samples = !have_wav && !have_generator && !have_config && !have_reply &&
        k_sem_take(&frame_available,K_NO_WAIT)==0;
    scope_batch2::Half half{scope_batch2::select_source(
        have_wav || have_generator || have_config || have_reply,have_samples,word,pipelined),false};
    if (have_wav) scope_wav::encode(packet,seq,wav_reply);
    else if (have_generator) scope_gen::encode(packet,seq,generator_reply);
    else if (have_config) scope_acq::encode(packet,seq,config_reply);
    else if (have_reply) scope_control::encode(packet,seq,reply);
    else {
        if (have_samples && word) {
            const unsigned slot=spi40_read;
            memcpy(packet,sample_ready[slot]->bytes,BLOCK_BYTES);
            half.final_node=spi40_last[slot];
            spi40_read=(slot+1U)%FRAME_SLOTS;
            // The DMA reads packet, never sample_ready. Only this scratch slot
            // may be returned now; the whole ADC node stays owned until EOT.
            if(scope_batch2::early_slot_release(half)) k_sem_give(&spi40_free);
        } else if (have_samples && pipelined) {
            memcpy(packet,sample_ready[read_frame]->bytes,BLOCK_BYTES);
            read_frame=(read_frame+1U)%FRAME_SLOTS;
        }
        data_frame(packet,seq,last_ping,spi_errors,bad_ping,short_transfers,
                   last_result,last_error,prepare_us,check_us);
        put16(packet+6,acquisition::native()?20:acquisition::period==133U?19:
              acquisition::single()?16:acquisition::bits==14?15:3);
        if (have_samples && half.source==scope_batch2::Source::Normal)
            memcpy(packet+48,ordinary_frame.bytes+48,BLOCK_BYTES-48-CRC_BYTES);
        else if(!have_samples) build_samples(packet,nullptr,0,0);
        seal(packet);
    }
    return half;
}

static bool valid_batch_command(const uint8_t *packet) {
    if (valid_ping(packet)) return true;
    scope_wav::Request wav_request{};
    scope_gen::Request generator_request{};
    scope_acq::Request config_request{};
    scope_control::Request request{};
    return scope_wav::decode(packet,BLOCK_BYTES,wav_request) ||
           scope_gen::decode(packet,BLOCK_BYTES,generator_request) ||
           scope_acq::decode(packet,BLOCK_BYTES,config_request) ||
           scope_control::decode(packet,BLOCK_BYTES,request);
}

static void process_batch_command(const uint8_t *packet) {
    if (valid_ping(packet)) { last_ping=get32(packet+8); return; }
    scope_control::Request request{};
    scope_acq::Request config_request{};
    scope_gen::Request generator_request{};
    scope_wav::Request wav_request{};
    if (scope_wav::decode(packet,BLOCK_BYTES,wav_request)) {
        if(k_msgq_num_free_get(&wav_replies)) {
            const auto result=wav::submit(wav_request);
            if(k_msgq_put(&wav_replies,&result,K_NO_WAIT)!=0) { acquisition::fail();ready=false; }
        } else { acquisition::fail();ready=false; }
    } else if (scope_gen::decode(packet,BLOCK_BYTES,generator_request)) {
        if(k_msgq_num_free_get(&generator_replies)) {
            const auto result=generator::submit(generator_request);
            if(k_msgq_put(&generator_replies,&result,K_NO_WAIT)!=0) { acquisition::fail();ready=false; }
        } else { acquisition::fail();ready=false; }
    } else if (scope_acq::decode(packet,BLOCK_BYTES,config_request)) {
        k_mutex_lock(&output_lock,K_FOREVER);
        if(k_msgq_num_free_get(&settings_replies)>=3U) {
            const auto accepted=settings.submit(config_request,
                !output_switch.pending() && output_mode==scope_control::SPI);
            if(k_msgq_put(&settings_replies,&accepted,K_NO_WAIT)!=0) {
                acquisition::fail();ready=false;
            }
        } else { acquisition::fail();ready=false; }
        k_mutex_unlock(&output_lock);
    } else if (scope_control::decode(packet,BLOCK_BYTES,request)) {
        k_mutex_lock(&output_lock,K_FOREVER);
        if(k_msgq_num_free_get(&control_replies)>=(reply_reserved?2U:3U)) {
            const auto accepted=request.mode==scope_control::UART &&
                (acquisition::native() || acquisition::single() || acquisition::period<32) ?
                scope_control::Reply{request.id,request.mode,output_mode,scope_control::REJECTED,
                                     scope_control::UNSUPPORTED,0} : settings.pending() ?
                scope_control::Reply{request.id,request.mode,output_mode,scope_control::REJECTED,
                                     scope_control::BUSY,0} : output_switch.submit(request);
            enqueue_reply(accepted);
            reply_reserved=output_switch.pending();
        } else { acquisition::fail();ready=false; }
        k_mutex_unlock(&output_lock);
    } else { ++bad_ping;acquisition::fail();ready=false; }
}

void loop() {
    if (!ready) { k_sleep(K_MSEC(100)); return; }
    // The core main thread's 32 KiB stack owns both aligned physical buffers.
    // The two logical halves live in tx_batch; DMA never reads producer frames.
    alignas(CONFIG_DCACHE_LINE_SIZE) uint8_t tx_batch[scope_spi16::physical_bytes];
    alignas(CONFIG_DCACHE_LINE_SIZE) uint8_t rx_batch[scope_spi16::physical_bytes];
    active_tx=tx_batch;physical_rx=rx_batch;
    wav::service();
    if ((acquisition::native() || acquisition::period==133U) && acquisition::threads_started &&
        !acquisition::fatal_errors && !acquisition::dropped_nodes &&
        !k_sem_count_get(&frame_available) && !k_msgq_num_used_get(&wav_replies) &&
        !k_msgq_num_used_get(&generator_replies) && !k_msgq_num_used_get(&settings_replies) &&
        !k_msgq_num_used_get(&control_replies)) {
        if(!high_rate_transport()) k_busy_wait(5);
        k_yield();return;
    }
    scope_batch2::Half halves[2];
    const uint32_t prepared_at=k_cycle_get_32();
    k_mutex_lock(&output_lock,K_FOREVER);
    batch_dma_word=word_transport();
    batch_dma_high=high_rate_transport();
    for(unsigned i=0;i<2;++i)
        halves[i]=prepare_batch_half(tx_batch+i*BLOCK_BYTES,sequence+i);
    k_mutex_unlock(&output_lock);
    prepare_us=elapsed_us(prepared_at);

    const int physical_result=exchange();
    const uint32_t checked_at=k_cycle_get_32();
    if(physical_result<0) {
        ++spi_errors;last_result=physical_result;
        last_error=fault_dma?-int32_t(0x2000000U|fault_dma):
            (fault_sr?-int32_t(0x10000U|(fault_sr&0xffffU)):physical_result);
        if(physical_result==-EMSGSIZE) ++short_transfers;
        acquisition::fail();ready=false;
    } else if(physical_result!=int(scope_spi16::physical_bytes)) {
        ++short_transfers;last_result=-EMSGSIZE;last_error=-EMSGSIZE;
        acquisition::fail();ready=false;
    } else if(!valid_batch_command(rx_batch) ||
              !valid_batch_command(rx_batch+BLOCK_BYTES)) {
        ++bad_ping;last_result=-EBADMSG;last_error=-EBADMSG;
        acquisition::fail();ready=false;
    } else {
        // Logical metadata retains the SCP1 contract (992), never physical 1984.
        last_result=scope_spi16::logical_result(physical_result);
        for(unsigned i=0;i<2 && ready;++i)
            process_batch_command(rx_batch+i*BLOCK_BYTES);
    }
    check_us=elapsed_us(checked_at);
    sequence+=2U;
    const auto credits=scope_batch2::credits_after_physical(halves,ready);
    for(unsigned i=0;i<credits.frames;++i) k_sem_give(&frame_sent);
    for(unsigned i=0;i<credits.nodes;++i) k_sem_give(&spi40_node_sent);
    // A failed DMA/command never returns node ownership. Board restart applies.
    if(!ready) for(;;) k_sleep(K_MSEC(100));
    if(halves[0].source==scope_batch2::Source::Idle &&
       halves[1].source==scope_batch2::Source::Idle) k_sleep(K_MSEC(1));
}
