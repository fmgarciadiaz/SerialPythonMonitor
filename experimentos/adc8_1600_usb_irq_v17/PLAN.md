# Separar USB de SPI en CPU0 a1,6000MS/s

Inventario: IRQ99dwc3 y123SPI efectivosCPU0; READY166casi exclusivamenteCPU0; solicitudes0-3. RelayCPU2. Único cambio: IRQ99USB aCPU1, resto igual. CPU2/performance/N3456/100ticks/SPI40,warm112/2s, MCU/relay originales. ABBA30s, Aafinidadoriginal,BUSB1, reiniciosindependientes; verificar solicitada/efectiva yguardarIRQantes/después. AmbosB íntegros,margen>=10%,pico<4desdearranque,slackpositivo ->60+3x120,cortar primerfallo. ControlA no borra fallos previos. No atribuir mejora exclusivamenteUSB sin considerar control.

Guardar afinidadoriginal yrestaurarenfinally antesderestaurarapp/relay/config/generador/governor. Verificar continuidad10s,reloj,hash. Si falla restauración declararerror yreparar. No cambiarIRQ123/166,prioridad,slotsni validaciones. Perfil106protegido.
