import math
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

import serial
from serial.tools import list_ports

import matplotlib

matplotlib.use("TkAgg")

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


BAUD_DEFAULT = 921600
VISIBLE_SAMPLES_DEFAULT = 500
VISIBLE_SAMPLES_MIN = 100
VISIBLE_SAMPLES_MAX = 50000
MAX_PLOT_POINTS = 2000
UPDATE_MS = 40
ARDUINO_KEYWORDS = (
    "arduino",
    "usbmodem",
    "usb serial",
    "ch340",
    "cp210",
    "ftdi",
    "wch",
)


class SerialMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Serial Monitor - Osciloscopio")
        self.root.geometry("1000x650")
        self.root.minsize(760, 480)

        self.serial_port = None
        self.reader_thread = None
        self.reader_stop = threading.Event()
        self.data_lock = threading.Lock()
        self.demo_mode = False
        self.start_time = time.perf_counter()
        self.sample_numbers = []
        self.series = {
            "ADC": [],
            "Voltaje (V)": [],
            "Muestra": [],
            "Tiempo (us)": [],
        }
        self.sample_count = 0
        self.invalid_count = 0
        self.series_minimum = {name: None for name in self.series}
        self.series_maximum = {name: None for name in self.series}
        self.visible_samples = VISIBLE_SAMPLES_DEFAULT
        self.selection_dirty = True
        self.last_rendered_count = -1
        self.last_render_timestamp = 0.0
        self.render_interval = 0.04
        self.render_pending = False
        self.trigger_enabled = tk.BooleanVar(value=False)
        self.trigger_source = tk.StringVar(value="Voltaje (V)")
        self.trigger_level = tk.StringVar(value="1.65")
        self.trigger_edge = tk.StringVar(value="Ascendente")
        self.trigger_previous_value = None
        self.trigger_start_index = None
        self.trigger_enabled_value = False
        self.trigger_source_value = "Voltaje (V)"
        self.trigger_level_value = 1.65
        self.trigger_edge_value = "Ascendente"
        self.trigger_message = None

        self.port_var = tk.StringVar()
        self.baud_var = tk.StringVar(value=str(BAUD_DEFAULT))
        self.status_var = tk.StringVar(value="Listo")
        self.selected_columns = {
            name: tk.BooleanVar(value=name == "Voltaje (V)")
            for name in self.series
        }

        self.build_controls()
        self.build_plot()
        arduino_detected = self.refresh_ports()
        self.update_plot()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        if arduino_detected:
            self.root.after(100, self.connect_serial)
        else:
            self.show_connection_error(
                "No se detecto ningun puerto Arduino. "
                "Selecciona otro puerto y pulsa Conectar."
            )

    def build_controls(self):
        controls = ttk.Frame(self.root, padding=8)
        controls.pack(fill=tk.X)
        controls.columnconfigure(1, weight=1)
        controls.columnconfigure(4, weight=1)

        ttk.Label(controls, text="Puerto:").grid(row=0, column=0, sticky="w")
        self.port_combo = ttk.Combobox(
            controls,
            textvariable=self.port_var,
            state="readonly",
        )
        self.port_combo.grid(row=0, column=1, sticky="ew", padx=(4, 12))

        ttk.Button(
            controls,
            text="Actualizar",
            command=self.refresh_ports,
        ).grid(row=0, column=2, padx=(0, 12))

        ttk.Label(controls, text="Baud:").grid(row=0, column=3, sticky="w")
        ttk.Entry(controls, textvariable=self.baud_var, width=10).grid(
            row=0, column=4, sticky="ew", padx=(4, 12)
        )

        ttk.Button(
            controls,
            text="Conectar",
            command=self.connect_serial,
        ).grid(row=0, column=5, padx=2)
        ttk.Button(
            controls,
            text="Demo",
            command=self.start_demo,
        ).grid(row=0, column=6, padx=2)
        ttk.Button(
            controls,
            text="Detener",
            command=self.stop_input,
        ).grid(row=0, column=7, padx=2)

        ttk.Label(
            controls,
            textvariable=self.status_var,
            foreground="#444444",
        ).grid(row=0, column=8, sticky="w", padx=(18, 0))

        columns_frame = ttk.LabelFrame(
            self.root,
            text="Columnas a graficar",
            padding=(8, 4),
        )
        columns_frame.pack(fill=tk.X, padx=8, pady=(0, 8))
        for index, (name, variable) in enumerate(self.selected_columns.items()):
            ttk.Checkbutton(
                columns_frame,
                text=name,
                variable=variable,
                command=self.redraw_selected_columns,
            ).grid(row=0, column=index, sticky="w", padx=(0, 16))

        x_frame = ttk.Frame(self.root, padding=(8, 0, 8, 8))
        x_frame.pack(fill=tk.X)
        x_frame.columnconfigure(1, weight=1)
        ttk.Label(x_frame, text="Muestras visibles:").grid(
            row=0, column=0, sticky="w"
        )
        self.x_scale = ttk.Scale(
            x_frame,
            from_=VISIBLE_SAMPLES_MIN,
            to=VISIBLE_SAMPLES_MAX,
            orient=tk.HORIZONTAL,
            command=self.change_visible_samples,
        )
        self.x_scale.set(VISIBLE_SAMPLES_DEFAULT)
        self.x_scale.grid(row=0, column=1, sticky="ew", padx=8)
        self.x_scale_value = tk.StringVar(value=str(VISIBLE_SAMPLES_DEFAULT))
        ttk.Label(x_frame, textvariable=self.x_scale_value, width=6).grid(
            row=0, column=2, sticky="e"
        )

        trigger_frame = ttk.LabelFrame(
            self.root,
            text="Trigger",
            padding=(8, 4),
        )
        trigger_frame.pack(fill=tk.X, padx=8, pady=(0, 8))
        ttk.Checkbutton(
            trigger_frame,
            text="Activar",
            variable=self.trigger_enabled,
            command=self.configure_trigger,
        ).pack(side=tk.LEFT)
        ttk.Label(trigger_frame, text="Señal:").pack(side=tk.LEFT, padx=(12, 4))
        ttk.Combobox(
            trigger_frame,
            textvariable=self.trigger_source,
            values=("ADC", "Voltaje (V)"),
            state="readonly",
            width=14,
        ).pack(side=tk.LEFT)
        ttk.Label(trigger_frame, text="Nivel:").pack(side=tk.LEFT, padx=(12, 4))
        ttk.Entry(trigger_frame, textvariable=self.trigger_level, width=8).pack(
            side=tk.LEFT
        )
        ttk.Label(trigger_frame, text="Flanco:").pack(side=tk.LEFT, padx=(12, 4))
        ttk.Combobox(
            trigger_frame,
            textvariable=self.trigger_edge,
            values=("Ascendente", "Descendente"),
            state="readonly",
            width=14,
        ).pack(side=tk.LEFT)

    def build_plot(self):
        figure = Figure(figsize=(10, 5.5), dpi=100)
        self.axis = figure.add_subplot(111)
        self.axis.set_title("Osciloscopio serial")
        self.axis.set_xlabel("Numero de muestra")
        self.axis.set_ylabel("Valor")
        self.axis.set_ylim(0, 3.3)
        self.axis.set_xlim(0, self.visible_samples)
        self.axis.grid(True, alpha=0.3)
        self.lines = {}
        figure.tight_layout()

        self.canvas = FigureCanvasTkAgg(figure, master=self.root)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        self.canvas.draw()

    def refresh_ports(self):
        available_ports = list(list_ports.comports())
        ports = [port.device for port in available_ports]
        self.port_combo["values"] = ports

        arduino_port = next(
            (
                port.device
                for port in available_ports
                if any(
                    keyword in " ".join(
                        str(value or "")
                        for value in (
                            port.device,
                            port.description,
                            port.manufacturer,
                            port.product,
                            port.hwid,
                        )
                    ).lower()
                    for keyword in ARDUINO_KEYWORDS
                )
            ),
            None,
        )

        if arduino_port:
            self.port_var.set(arduino_port)
            self.status_var.set(f"Arduino seleccionado: {arduino_port}")
        elif ports and self.port_var.get() not in ports:
            self.port_var.set(ports[0])
            self.status_var.set("Puerto seleccionado; Arduino no identificado")
        elif not ports:
            self.port_var.set("")
            self.status_var.set("No hay puertos: usa Demo o conecta Arduino")

        return arduino_port is not None

    def show_connection_error(self, message):
        self.status_var.set("Error de conexion")
        self.root.after(
            150,
            lambda: messagebox.showerror("No se pudo conectar", message),
        )

    def connect_serial(self):
        self.stop_input()

        port = self.port_var.get().strip()
        if not port:
            messagebox.showwarning("Puerto serial", "Selecciona un puerto serial.")
            return

        try:
            baud = int(self.baud_var.get())
            self.serial_port = serial.Serial(port, baud, timeout=0.1)
            self.serial_port.reset_input_buffer()
        except (ValueError, serial.SerialException) as error:
            self.serial_port = None
            self.show_connection_error(str(error))
            return

        self.clear_data()
        self.reader_stop.clear()
        self.reader_thread = threading.Thread(
            target=self.serial_reader_loop,
            daemon=True,
        )
        self.reader_thread.start()
        self.status_var.set(f"Conectado a {port}")

    def start_demo(self):
        self.stop_input()
        self.clear_data()
        self.demo_mode = True
        self.start_time = time.perf_counter()
        self.status_var.set("Modo demo activo")

    def stop_input(self):
        self.demo_mode = False
        self.reader_stop.set()
        if self.serial_port is not None:
            self.serial_port.close()
            self.serial_port = None
        self.reader_thread = None
        self.status_var.set("Detenido")

    def clear_data(self):
        self.sample_numbers.clear()
        for values in self.series.values():
            values.clear()
        for name in self.series:
            self.series_minimum[name] = None
            self.series_maximum[name] = None
        self.sample_count = 0
        self.invalid_count = 0
        self.trigger_previous_value = None
        self.trigger_start_index = None
        self.trigger_message = None
        self.trigger_enabled_value = False
        self.start_time = time.perf_counter()

    def configure_trigger(self):
        try:
            trigger_level = float(self.trigger_level.get())
        except ValueError:
            self.status_var.set("Nivel de trigger invalido")
            return

        with self.data_lock:
            self.trigger_enabled_value = self.trigger_enabled.get()
            self.trigger_source_value = self.trigger_source.get()
            self.trigger_level_value = trigger_level
            self.trigger_edge_value = self.trigger_edge.get()
            self.trigger_previous_value = None
            self.trigger_start_index = None
            self.trigger_message = None
        if self.trigger_enabled.get():
            self.status_var.set("Trigger armado; esperando cruce")
        else:
            self.status_var.set("Trigger desactivado")

    def check_trigger(self, values):
        if not self.trigger_enabled_value:
            return

        source_name = self.trigger_source_value
        if source_name not in values:
            source_name = "Voltaje (V)"

        level = self.trigger_level_value
        value = values[source_name]
        previous = self.trigger_previous_value
        self.trigger_previous_value = value

        if self.trigger_start_index is not None:
            if len(self.sample_numbers) - self.trigger_start_index >= self.visible_samples:
                self.trigger_start_index = None
                self.trigger_previous_value = None
            return

        if previous is None:
            return

        rising = previous < level <= value
        falling = previous > level >= value
        crossed = rising if self.trigger_edge_value == "Ascendente" else falling
        if crossed:
            self.trigger_start_index = max(0, len(self.sample_numbers) - 1)
            self.trigger_message = f"Trigger: cruce en muestra {self.sample_numbers[-1]}"

    def serial_reader_loop(self):
        while not self.reader_stop.is_set() and self.serial_port is not None:
            try:
                raw_line = self.serial_port.readline()
            except serial.SerialException:
                self.trigger_message = "Conexion serial interrumpida"
                break
            if not raw_line:
                continue

            line = raw_line.decode("utf-8", errors="ignore").strip()
            parts = line.split(",")

            if len(parts) != 4:
                if line and not line.lower().startswith("estado"):
                    with self.data_lock:
                        self.invalid_count += 1
                continue

            try:
                muestra = int(parts[1])
                tiempo_us = int(parts[2])
                adc = int(parts[3])
            except ValueError:
                with self.data_lock:
                    self.invalid_count += 1
                continue

            self.append_sample(muestra, tiempo_us, adc)

    def append_sample(self, muestra, tiempo_us, adc):
        with self.data_lock:
            self.sample_numbers.append(len(self.sample_numbers) + 1)
            values = {
                "ADC": adc,
                "Voltaje (V)": adc * 3.3 / 4095,
                "Muestra": muestra,
                "Tiempo (us)": tiempo_us,
            }
            for name, value in values.items():
                self.series[name].append(value)
                if self.series_minimum[name] is None:
                    self.series_minimum[name] = value
                    self.series_maximum[name] = value
                else:
                    self.series_minimum[name] = min(self.series_minimum[name], value)
                    self.series_maximum[name] = max(self.series_maximum[name], value)
            self.sample_count += 1
            self.check_trigger(values)

    def add_demo_sample(self):
        elapsed = time.perf_counter() - self.start_time
        voltage = 1.65 + 1.25 * math.sin(elapsed * 4.0)
        voltage += 0.12 * math.sin(elapsed * 31.0)
        sample = self.sample_count + 1
        voltage = max(0.0, min(3.3, voltage))
        self.append_sample(sample, int(elapsed * 1_000_000), voltage * 4095 / 3.3)

    def redraw_selected_columns(self):
        for line in self.lines.values():
            line.remove()
        self.lines.clear()

        selected = [
            name for name, variable in self.selected_columns.items() if variable.get()
        ]
        for index, name in enumerate(selected):
            x_values, y_values = self.visible_plot_data(name)
            line, = self.axis.plot(
                x_values,
                y_values,
                linewidth=1.6,
                label=name,
            )
            self.lines[name] = line

        if selected:
            self.axis.legend(loc="upper left")
        elif self.axis.legend_:
            self.axis.legend_.remove()

        self.update_vertical_scale(selected, recompute=True)
        self.selection_dirty = False
        self.canvas.draw_idle()

    def change_visible_samples(self, value):
        self.visible_samples = max(VISIBLE_SAMPLES_MIN, int(float(value)))
        self.x_scale_value.set(str(self.visible_samples))
        self.selection_dirty = True
        if self.trigger_enabled.get():
            self.trigger_start_index = None
            self.trigger_previous_value = None

    def visible_slice(self):
        if not self.sample_numbers:
            return 0, 0

        right = len(self.sample_numbers)
        if self.trigger_enabled.get() and self.trigger_start_index is not None:
            left = max(0, self.trigger_start_index - self.visible_samples + 1)
            return left, right
        left = max(0, right - self.visible_samples)
        return left, right

    def visible_plot_data(self, name):
        start, end = self.visible_slice()
        point_count = end - start
        step = max(1, math.ceil(point_count / MAX_PLOT_POINTS))
        with self.data_lock:
            sample_numbers = self.sample_numbers[start:end:step]
            series_values = self.series[name][start:end:step]
        return (sample_numbers, series_values)

    def update_vertical_scale(self, selected=None, recompute=False):
        if selected is None:
            selected = list(self.lines)

        limits = [
            (self.series_minimum[name], self.series_maximum[name])
            for name in selected
            if self.series_minimum[name] is not None
        ]
        if not limits:
            self.axis.set_ylim(0, 3.3)
            self.axis.set_ylabel("Valor")
            return

        lower = min(pair[0] for pair in limits)
        upper = max(pair[1] for pair in limits)
        if lower == upper:
            padding = max(abs(upper) * 0.1, 1.0)
        else:
            padding = (upper - lower) * 0.1
        target_lower = lower - padding
        target_upper = upper + padding
        current_lower, current_upper = self.axis.get_ylim()
        if recompute:
            self.axis.set_ylim(target_lower, target_upper)
        else:
            self.axis.set_ylim(
                min(current_lower, target_lower),
                max(current_upper, target_upper),
            )
        self.axis.set_ylabel(", ".join(selected))

    def update_plot(self):
        if self.demo_mode:
            self.add_demo_sample()
        elif self.trigger_message:
            self.status_var.set(self.trigger_message)
            self.trigger_message = None

        if self.selection_dirty:
            self.redraw_selected_columns()

        has_new_data = self.sample_count != self.last_rendered_count
        if has_new_data:
            self.render_pending = True

        trigger_has_window = (
            not self.trigger_enabled.get()
            or self.trigger_start_index is not None
        )
        now = time.perf_counter()

        if self.render_pending and trigger_has_window:
            if has_new_data or self.selection_dirty:
                for name, line in self.lines.items():
                    x_values, y_values = self.visible_plot_data(name)
                    line.set_data(x_values, y_values)

                self.update_vertical_scale()

                if self.sample_numbers and not self.trigger_enabled.get():
                    right = max(self.visible_samples, len(self.sample_numbers))
                    left = max(0, right - self.visible_samples)
                    self.axis.set_xlim(left, right)
                elif self.sample_numbers and self.trigger_start_index is not None:
                    left_index = max(0, self.trigger_start_index - self.visible_samples + 1)
                    right_index = len(self.sample_numbers)
                    left_value = self.sample_numbers[left_index]
                    right_value = self.sample_numbers[right_index - 1]
                    self.axis.set_xlim(left_value, right_value)

                self.axis.set_title(
                    f"Osciloscopio serial | muestras: {self.sample_count} | "
                    f"invalidas: {self.invalid_count}"
                )

            if now - self.last_render_timestamp >= self.render_interval:
                self.last_render_timestamp = now
                self.last_rendered_count = self.sample_count
                self.render_pending = False
                self.canvas.draw_idle()

        self.root.after(UPDATE_MS, self.update_plot)

    def close(self):
        self.reader_stop.set()
        if self.serial_port is not None:
            self.serial_port.close()
        self.root.destroy()


def main():
    root = tk.Tk()
    SerialMonitorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
