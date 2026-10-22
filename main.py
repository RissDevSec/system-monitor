import os
import psutil
import datetime
from notifier import message_warning

PROCFS_PATH = os.getenv("PROCFS_PATH", "/proc")
DISK_PATH = os.getenv("DISK_PATH", "/")
psutil.PROCFS_PATH = PROCFS_PATH

state = {
    "cpu": False,
    "ram": False,
    "disk": False
}

def get_system():
    cpu = round(psutil.cpu_percent(interval=2))
    ram = psutil.virtual_memory()
    disk = round(psutil.disk_usage(DISK_PATH).percent)

    return {
        "cpu": cpu,
        "ram": round(ram.percent),
        "ram_used": ram.used / (2**30),
        "ram_total": ram.total / (2**30),
        "disk": disk
    }

def evaluate_metric(key, percent, display_base, label, threshold=80):

    is_warning = percent >= threshold

    if is_warning:
        display = f"{display_base} \N{WARNING SIGN} WARNING"
    else:
        display = display_base

    alert_line = None
    if is_warning and not state[key]:
        alert_line = f"\N{WARNING SIGN} WARNING - {label} almost full!\n"
        state[key] = True
    elif not is_warning and state[key]:
        alert_line = f"\N{CHECK MARK} INFO - {label} back to normal\n"
        state[key] = False

    return display, alert_line

def check_system():
    data = get_system()
    message = ""

    cpu_display, cpu_alert = evaluate_metric("cpu", data["cpu"], f"{data['cpu']}%", "CPU")
    if cpu_alert: message += cpu_alert
    data["cpu"] = cpu_display

    ram_base = f"{data['ram']}% ({data['ram_used']:.1f}/{data['ram_total']:.1f} GB)"
    ram_display, ram_alert = evaluate_metric("ram", data["ram"], ram_base, "RAM")
    if ram_alert: message += ram_alert
    data["ram"] = ram_display

    disk_display, disk_alert = evaluate_metric("disk", data["disk"], f"{data['disk']}%", "Disk")
    if disk_alert: message += disk_alert
    data["disk"] = disk_display

    if message: message_warning(message)
    return data

def main():
    print("System monitor started. Checking every 2 seconds. Press Ctrl+C to stop.")

    try:
        while True:
            data = check_system()
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] CPU: {data['cpu']} | RAM: {data['ram']} | Disk: {data['disk']}\n")
    except KeyboardInterrupt:
        print("\nStopped.")

if __name__ == "__main__":
    main()