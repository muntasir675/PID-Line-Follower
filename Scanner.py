import asyncio
import tkinter as tk
from bleak import BleakClient

    



# =============== CONFIG =================
DEVICE_ADDRESS = "D3:52:88:07:0D:31"
RX_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"




# Default values
DEFAULT_KP = 75
DEFAULT_KI = 1  # 0.1 actual (1/10)
DEFAULT_KD = 10
DEFAULT_SPEED = 100
# ========================================





class ControllerApp:
    def __init__(self, root, loop):
        self.root = root
        self.loop = loop
        self.client = None
        
        # Store previous values
        self.prev_kp = DEFAULT_KP
        self.prev_ki = DEFAULT_KI
        self.prev_kd = DEFAULT_KD
        self.prev_speed = DEFAULT_SPEED





        self.root.title("ZETA Controller")
        self.root.geometry("450x390")





        self.status_var = tk.StringVar(value="Connecting...")
        tk.Label(root, textvariable=self.status_var, fg="orange", font=("Arial", 12)).pack(pady=5)





        frame = tk.Frame(root)
        frame.pack(pady=5)





        # Kp slider: 40-100
        tk.Label(frame, text="Kp (p)").grid(row=0, column=0, sticky="w")
        self.kp_var = tk.IntVar(value=DEFAULT_KP)
        tk.Scale(frame, from_=40, to=100, orient="horizontal", length=300, variable=self.kp_var).grid(row=0, column=1)





        # Ki slider: 0-10 (actual Ki = value/10, range 0.0-1.0)
        tk.Label(frame, text="Ki (i)").grid(row=1, column=0, sticky="w")
        self.ki_raw_var = tk.IntVar(value=DEFAULT_KI)
        self.ki_label_var = tk.StringVar(value=f"Ki = {DEFAULT_KI/10:.1f}")
        tk.Scale(frame, from_=0, to=10, orient="horizontal", length=300, variable=self.ki_raw_var, command=self._update_ki_label).grid(row=1, column=1)
        tk.Label(frame, textvariable=self.ki_label_var).grid(row=1, column=2, padx=5)





        # Kd slider: 0-50
        tk.Label(frame, text="Kd (d)").grid(row=2, column=0, sticky="w")
        self.kd_var = tk.IntVar(value=DEFAULT_KD)
        tk.Scale(frame, from_=0, to=50, orient="horizontal", length=300, variable=self.kd_var).grid(row=2, column=1)





        # Speed slider: 90-150
        tk.Label(frame, text="Speed (v)").grid(row=3, column=0, sticky="w")
        self.v_var = tk.IntVar(value=DEFAULT_SPEED)
        tk.Scale(frame, from_=90, to=150, orient="horizontal", length=300, variable=self.v_var).grid(row=3, column=1)





        self.cmd_var = tk.StringVar(value="Command: ")
        tk.Label(root, textvariable=self.cmd_var, font=("Consolas", 10)).pack(pady=5)





        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=5)
        
        tk.Button(btn_frame, text="Confirm Send", command=self.on_confirm, bg="green", fg="white", width=12).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Reset", command=self.on_reset, bg="orange", fg="white", width=12).pack(side="left", padx=5)
        tk.Button(btn_frame, text="STOP", command=self.on_stop, bg="red", fg="white", width=12).pack(side="left", padx=5)
        
        btn_frame2 = tk.Frame(root)
        btn_frame2.pack(pady=5)
        tk.Button(btn_frame2, text="Previous Values", command=self.on_previous, bg="blue", fg="white", width=12).pack(padx=5)





        self.root.after(50, self.periodic_update)





    def _update_ki_label(self, _=None):
        ki = self.ki_raw_var.get() / 10.0
        self.ki_label_var.set(f"Ki = {ki:.1f}")
        self._update_cmd_preview()





    def _update_cmd_preview(self):
        cmd = f"p{self.kp_var.get()} d{self.kd_var.get()} i{self.ki_raw_var.get()} v{self.v_var.get()} "
        self.cmd_var.set(f"Command: {cmd}")





    def on_confirm(self):
        # Save current values before sending
        self.prev_kp = self.kp_var.get()
        self.prev_ki = self.ki_raw_var.get()
        self.prev_kd = self.kd_var.get()
        self.prev_speed = self.v_var.get()
        
        cmd = f"p{self.kp_var.get()} d{self.kd_var.get()} i{self.ki_raw_var.get()} v{self.v_var.get()} "
        asyncio.run_coroutine_threadsafe(self._send_command(cmd), self.loop)





    def on_reset(self):
        # Save current values before reset
        self.prev_kp = self.kp_var.get()
        self.prev_ki = self.ki_raw_var.get()
        self.prev_kd = self.kd_var.get()
        self.prev_speed = self.v_var.get()
        
        self.kp_var.set(DEFAULT_KP)
        self.ki_raw_var.set(DEFAULT_KI)
        self.kd_var.set(DEFAULT_KD)
        self.v_var.set(DEFAULT_SPEED)
        self._update_ki_label()
        # Instantly send reset values
        reset_cmd = f"p{DEFAULT_KP} d{DEFAULT_KD} i{DEFAULT_KI} v{DEFAULT_SPEED} "
        asyncio.run_coroutine_threadsafe(self._send_command(reset_cmd), self.loop)




    def on_stop(self):
        # Save current values before stopping
        self.prev_kp = self.kp_var.get()
        self.prev_ki = self.ki_raw_var.get()
        self.prev_kd = self.kd_var.get()
        self.prev_speed = self.v_var.get()
        
        # Set all sliders to 0
        self.kp_var.set(0)
        self.ki_raw_var.set(0)
        self.kd_var.set(0)
        self.v_var.set(0)
        self._update_ki_label()
        # Instantly send stop command
        stop_cmd = "p0 d0 i0 v0 "
        asyncio.run_coroutine_threadsafe(self._send_command(stop_cmd), self.loop)


    def on_previous(self):
        # Restore previous values and send
        self.kp_var.set(self.prev_kp)
        self.ki_raw_var.set(self.prev_ki)
        self.kd_var.set(self.prev_kd)
        self.v_var.set(self.prev_speed)
        self._update_ki_label()
        # Instantly send previous values
        prev_cmd = f"p{self.prev_kp} d{self.prev_kd} i{self.prev_ki} v{self.prev_speed} "
        asyncio.run_coroutine_threadsafe(self._send_command(prev_cmd), self.loop)





    async def _send_command(self, cmd_string: str):
        data = cmd_string.encode("ascii")
        await self.client.write_gatt_char(RX_UUID, data, response=False)
        print(f"Sent: {repr(data)}")
        self.status_var.set(f"Sent: {cmd_string}")





    def periodic_update(self):
        self._update_cmd_preview()
        self.root.after(50, self.periodic_update)





async def connect(app):
    client = BleakClient(DEVICE_ADDRESS)
    await client.connect()
    app.client = client
    app.status_var.set("Connected")
    print("Connected")





async def main_async():
    loop = asyncio.get_event_loop()
    root = tk.Tk()
    app = ControllerApp(root, loop)
    asyncio.create_task(connect(app))
    while True:
        root.update()
        await asyncio.sleep(0.01)





asyncio.run(main_async())
