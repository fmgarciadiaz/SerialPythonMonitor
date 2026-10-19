# ADC14 RADIO+A0 a851063 — nodos5952

Se mantiene ticks188/160MHz, tasaefectiva851063,829787samples/s; se cambiaN1984→5952 en perfilprivado ypolicyCPUhighrateexacta.12frames496por nodo,6,9936ms por nodo. Timestamp47616+scratch1984=49600<65536;ADC23808<32768;cola4×5952<4×8192. HeaderMCU native_profiles/high_rate cambian, conrespaldo/restauraciónidentidad. No alegarMCUunchanged: docstring heredada esincorrecta, mcu_hashes y sources.zip explicitan cambio.

CandidatosanterioresCPUsolo yCPU+refillhostfallaron tercera120; estánrestaurados ynoincorporados. Hostdeesteensayo mantiene ráfaga16/6ms/créditos30 y comparaciónloops fuera lockaudio,outputsnapshotconlockbreve. No se cambiaCRC ni se toleranpérdidas.

Pilot130934 no midió: UIrechazóperfilprivate conStopIteration; Qrestaurada. Retry131346 corrige sóloaccesodiagnóstico, mantieneperfilprivadoenmemoria. Pantalla60s pasó con19,48%cola2 yslack875276. Tres120pendientesalcierredeesta nota. Report.ok esintegridad; headroom_ok porfila se evalúaaparte(>=10%,cola<4,slack>0). No promoverantescampañacompletarestaurada ypruebasenproducción.

Si pasa: instalarfuentesexactasMCU/relay/host,actualizarúnicaentradaJSON14ticks188aN5952sinagregarnuevatasa yretirarlímiteprovisional599. Verificaridentidadbinariocalificado yregresión8/10/12/14,A020/40 yFILTER; rollbackcompletosinconfirmacionesredundantes. Qlibresinmonitoralcomenzar.
