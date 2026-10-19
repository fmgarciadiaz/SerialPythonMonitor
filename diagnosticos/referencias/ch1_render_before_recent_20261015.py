"""Reference with cached CH1 label/style, before recent-history trigger search."""
def render_frame(self):
        if not self.is_running:
            return

        active_columns = [col for col, checked in self.selected_columns.items() if checked]
        audio_names={'RADIO'}
        if self.filter_source.currentText()=='RADIO':audio_names.add('FILTER')
        if self.spectral.mode==0 and set(active_columns)&audio_names and set(active_columns)-audio_names:
            self._render_mixed_temporal(active_columns,audio_names);return
        if self.spectral.mode==0 and (set(active_columns)&audio_names or
                                      self.trigger_enabled and self._is_audio_channel(self.trigger_source)):
            self._render_radio_audio(active_columns,audio_names)
            return
        if self.single_shot_armed and self.spectral.mode in (1,2) and self._is_audio_channel(self.trigger_source):
            selected=self.spectral.transfer_pair() if self.spectral.mode==1 and self.spectral.fft_mode.currentText()=='Transfer' else tuple(c.currentText() for c in self.spectral.channels)
            self._render_radio_audio([c for c in selected if c!='Ninguno'],audio_names)
            return
        total_samples = len(self.sample_numbers)
        if total_samples < 2:
            return
        if not active_columns and self.spectral.mode==0:
            for curve in self.line_items.values():curve.setVisible(False)
            return

        # Spectral modes display their own curves. Keep shared measurements/Fs
        # current, but do not prepare and draw a hidden temporal trace at 60 Hz.
        # SINGLE still uses the existing trigger/freeze path in any mode.
        if self.spectral.mode != 0 and not self.single_shot_armed:
            self._roll_position = None
            fs_hz, dt_us, fs_text = self._calculate_sample_rate()
            self.lbl_top_fs.setText(fs_text)
            if time.perf_counter()-getattr(self, '_last_measurement_update', 0) >= .1:
                end = total_samples
                start = max(0, end-self.h_scale)
                meas_col = self.active_meas_channel if self.active_meas_channel in active_columns or not active_columns else active_columns[0]
                slices = {name:self._window_values(self.series[name], start, end)
                          for name in (meas_col, 'Tiempo (us)') if name in self.series and len(self.series[name])>=end}
                self._update_live_measurements(slices, active_columns)
            return

        if self.selection_dirty or not self.line_items:
            self._update_curve_items(active_columns)

        w = self.h_scale

        # MODO CONTINUO (Roll) vs MODO TRIGGER (Estabilizado con fase fija)
        if not self.trigger_enabled:
            # 1. Modo Continuo: El osciloscopio hace barrido de izquierda a derecha (Roll)
            end_pos = max(w, total_samples + self.h_pos)
            end_pos = min(end_pos, total_samples)
            fraction = 0.0
            if self.h_pos == 0 and total_samples >= w:
                visual_end = self._roll_end_position(total_samples, time.perf_counter())
                end_pos = int(visual_end)
                fraction = visual_end - end_pos
            else:
                self._roll_position = None
            start_pos = max(0, end_pos - w)

            count = end_pos - start_pos

            # ---- EJE X: MUESTRAS o TIEMPO REAL (µs) ----
            if self.x_axis_time_mode:
                t_deque = self.series.get("Tiempo (us)")
                if t_deque and len(t_deque) >= end_pos and count > 0:
                    t_slice = self._window_values(t_deque, start_pos, end_pos)
                    t0 = t_slice[0]
                    x_plot = np.asarray(t_slice, dtype=float) - t0
                    x_end = x_plot[-1] if len(x_plot) else w
                    # Trasladar también fracciones de muestra, sin interpolar Y.
                    dt_visual = (t_slice[1] - t0) if count > 1 else 0.0
                    x_plot -= fraction * dt_visual
                    self.plot_widget.setXRange(0, x_end, padding=0.02)
                    self._set_temporal_x_label("Tiempo relativo en ventana (µs)")
                else:
                    # Sin timestamps: fallback a muestras silenciosamente
                    x_plot = np.arange(count, dtype=float) - fraction
                    self.plot_widget.setXRange(0, w, padding=0.0)
                    self._set_temporal_x_label("Muestras en ventana (sin timestamps)")
            else:
                x_plot = np.arange(count, dtype=float) - fraction
                self.plot_widget.setXRange(0, w, padding=0.0)
                self._set_temporal_x_label("Muestras en ventana")

            y_slices = {}
            for col in active_columns:
                series_deque = self.series.get(col)
                if series_deque and len(series_deque) >= end_pos:
                    y_slices[col] = self._window_values(series_deque, start_pos, end_pos)
                else:
                    y_slices[col] = []

            self.trigger_t_marker.setVisible(False)

        else:
            self._roll_position = None
            # 2. Modo Trigger: El disparo se fija en X = 0 (Pre-trigger con H-Pos)
            shift = self.h_pos
            pre_samples = max(0, min(w - 1, int(w * 0.10) - shift))
            post_samples = w - pre_samples

            # ---- EJE X en modo TRIGGER: Muestras relativas o µs relativos al T=0 ----
            if self.x_axis_time_mode and self.current_dt_us > 0:
                dt = self.current_dt_us
                x_plot = np.arange(-pre_samples, post_samples, dtype=float) * dt
                self.plot_widget.setXRange(x_plot[0], x_plot[-1], padding=0.0)
            else:
                x_plot = np.arange(-pre_samples, post_samples, dtype=float)
                self.plot_widget.setXRange(-pre_samples, post_samples, padding=0.0)

            self.trigger_t_marker.setValue(0)
            self.trigger_t_marker.setVisible(True)

            source = self.trigger_source
            src_deque = self.series.get(source)
            n = len(src_deque) if src_deque else 0

            found_t_idx = None
            if src_deque and n >= (pre_samples + post_samples):
                required_post = post_samples
                if self.single_shot_armed and self.spectral.mode in (1, 2):
                    fft_samples = int(self.spectral.size.currentText())
                    required_post = max(required_post, fft_samples - fft_samples // 10)
                end_search = n - required_post
                search_window = min(n - required_post - pre_samples, max(3000, w * 4))
                start_search = end_search - search_window

                if start_search >= pre_samples and end_search > start_search:
                    search_vals = self._window_values(src_deque, start_search - 1, end_search + 1)
                    level = self.trigger_level
                    is_rising = (self.trigger_edge == "Ascendente")
                    is_adc = "ADC" in source
                    hysteresis = 20.0 if is_adc else 0.015
                    i = last_trigger_crossing(search_vals, level, is_rising, hysteresis)
                    if i is not None:
                        found_t_idx = (start_search-1)+i

            now = time.perf_counter()
            if found_t_idx is not None:
                slice_start = found_t_idx - pre_samples
                slice_end = found_t_idx + post_samples

                y_slices = {}
                for col in active_columns:
                    col_deque = self.series.get(col)
                    if col_deque and len(col_deque) >= slice_end:
                        y_slices[col] = self._window_values(col_deque, slice_start, slice_end)
                    else:
                        y_slices[col] = []

                self.frozen_frame = (x_plot, y_slices)
                self.last_trigger_time = now

                is_adc = "ADC" in source
                unit = "" if is_adc else "V"
                lvl_str = f"{int(self.trigger_level)}" if is_adc else f"{number(self.trigger_level, formats.n_2f)}"
                self._set_temporal_trigger_status(
                    f"● Disparo ({source} {self.trigger_edge} @ {lvl_str}{unit})"
                )
                if self.x_axis_time_mode and self.current_dt_us > 0:
                    self._set_temporal_x_label("Tiempo relativo al Trigger (µs, T=0)")
                else:
                    self._set_temporal_x_label("Muestras relativas al Trigger (T=0)")

                if self.single_shot_armed:
                    if self.spectral.mode in (1, 2) and not self.spectral.capture_single(found_t_idx):
                        self.spectral.info.setText('SINGLE · esperando un bloque espectral válido.')
                        return
                    self.single_shot_armed = False
                    self._set_single_state('captured')
                    self.is_running = False
                    self.run_stop_btn.setChecked(False)
                    self.run_stop_btn.setText("⏹ STOP")
                    self._set_connection_status("Pantalla congelada (SINGLE capturado)")
                    self.status_label.setStyleSheet("""
                        QLabel {
                            background:#171920;
                            border:1px solid #323946;
                            border-radius: 6px;
                            padding: 2px 8px;
                            color:#aeb8c8;
                            font-weight:normal;
                            font-size: 11px;
                        }
                    """)

            elif self.frozen_frame is not None and (self.trigger_mode == "Normal" or (now - self.last_trigger_time) < 0.3):
                _, y_slices = self.frozen_frame
                if self.trigger_mode == "Normal":
                    self._set_temporal_trigger_status("● Esperando disparo (Normal)…")
            else:
                # Timeout en Auto mode (fallback continuo)
                end_pos = max(w, total_samples + self.h_pos)
                end_pos = min(end_pos, total_samples)
                start_pos = max(0, end_pos - w)
                y_slices = {
                    col: self._window_values(self.series[col], start_pos, end_pos)
                    for col in active_columns if col in self.series and len(self.series[col])>=end_pos
                }
                self._set_temporal_trigger_status("● Auto: buscando disparo · ajustar nivel")
                if self.x_axis_time_mode:
                    self._set_temporal_x_label("Tiempo en ventana (µs, Buscando Trigger)")
                else:
                    self._set_temporal_x_label("Muestras en ventana (Buscando Trigger)")

        # Cached independent window arrays allow changing detail in STOP
        # without advancing the capture or changing its measurements.
        if len(x_plot):
            self._last_display_frame = (x_plot, y_slices, tuple(active_columns))
            self._draw_display_frame(*self._last_display_frame)

        self._update_live_measurements(y_slices, active_columns)

        # ---------------------------------------------------------
        # ACTUALIZACIÓN DE FRECUENCIA DE MUESTREO (Fs y dt)
        # ---------------------------------------------------------
        fs_hz, dt_us, fs_text = self._calculate_sample_rate()
        self.lbl_top_fs.setText(fs_text)
        if dt_us > 0:
            if dt_us < 1000.0:
                tip = f"Frecuencia de Muestreo: {number(fs_hz, formats.n_1f)} Hz\nPeriodo entre muestras: {number(dt_us, formats.n_1f)} µs"
            else:
                tip = f"Frecuencia de Muestreo: {number(fs_hz, formats.n_1f)} Hz\nPeriodo entre muestras: {number(dt_us/1000.0, formats.n_2f)} ms"
            self.lbl_top_fs.setToolTip(tip)
            self.config_rate_combo.setToolTip(tip)

        # Medición de FPS
        self.render_count += 1
        now_calc = time.perf_counter()
        if (now_calc - self.last_fps_calc) >= 1.0:
            self.current_fps = self.render_count / (now_calc - self.last_fps_calc)
            self.render_count = 0
            self.last_fps_calc = now_calc
            mode_str = "RUN" if self.is_running else "STOP"
            self.plot_widget.setTitle(
                f"SCOPE V17 [{mode_str}] | Muestras: {number(self.sample_counter, formats.n_)} | "
                f"Ventana: {number(self.h_scale, formats.n_)} | Fs: {fs_text} | FPS: {number(self.current_fps, formats.n_1f)}"
            )
