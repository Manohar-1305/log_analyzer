import os
import platform
import argparse
from datetime import datetime
import json
import smtplib
from email.mime.text import MIMEText
import subprocess

def parse_args():
    parser = argparse.ArgumentParser(description="System Monitor and Alert Tool")
    parser.add_argument('-k', '--keywords', type=str, nargs='+', default=["warn", "critical", "error", "fail"], help="Alert keywords (unused here but kept for compatibility)")
    parser.add_argument('--save-summary', action='store_true', help="Save summary to JSON")
    parser.add_argument('--get-beep', action='store_true', help="Beep if alert found")
    parser.add_argument('--get-email', action='store_true', help="Send summary via email")
    parser.add_argument('--recipient', type=str, help="Email recipient")
    args = parser.parse_args()

    if args.get_email and not args.recipient:
        parser.error("--recipient is required when using --get-email")
    return args

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

def send_email(subject, body, recipient):
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        print("❌ EMAIL_ADDRESS and EMAIL_PASSWORD must be set in environment.")
        return
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = recipient
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
        print(f"📧 Email sent to {recipient}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

def beep():
    if platform.system() == 'Windows':
        import winsound
        winsound.Beep(1000, 500)
    else:
        print('\a')
        print("Beep triggered!")

def get_cpu_usage():
    output = subprocess.getoutput("top -bn1 | grep 'Cpu(s)' | awk '{print $2 + $4}'")
    try:
        return float(output)
    except:
        return 0.0

def get_memory_usage():
    output = subprocess.getoutput("free -m | grep 'Mem' | awk '{print (($3-$6)/$2)*100}'")
    try:
        return float(output)
    except:
        return 0.0

def get_disk_usage():
    output = subprocess.getoutput("df -h / | awk 'NR==2{print $5}'")
    return output.strip()

def check_cpu_temperature():
    # This depends on your system - on Linux, try reading /sys/class/thermal/thermal_zone*/temp
    # Here we mock it for example
    try:
        temp_raw = subprocess.getoutput("cat /sys/class/thermal/thermal_zone0/temp")
        temp_c = int(temp_raw) / 1000.0
        return temp_c
    except:
        return None

def check_service_status(service_name):
    # Example: check if service is active (mock here)
    try:
        status = subprocess.getoutput(f"systemctl is-active {service_name}")
        return status.strip()
    except:
        return "unknown"

def monitor_system():
    alerts = []
    summary = {}

    cpu = get_cpu_usage()
    mem = get_memory_usage()
    disk = get_disk_usage()
    cpu_temp = check_cpu_temperature()
    service_status = check_service_status("your-service-name")  # Replace with actual service to monitor

    summary['cpu_usage_percent'] = cpu
    summary['memory_usage_percent'] = mem
    summary['disk_usage'] = disk
    summary['cpu_temperature_celsius'] = cpu_temp
    summary['service_status'] = service_status

    print(f"CPU Usage: {cpu:.2f}%")
    print(f"Memory Usage: {mem:.2f}%")
    print(f"Disk Usage: {disk}")
    if cpu_temp is not None:
        print(f"CPU Temperature: {cpu_temp:.1f}°C")
    else:
        print("CPU Temperature: Not available")

    print(f"Service 'your-service-name' status: {service_status}")

    # Check thresholds and generate alerts
    if cpu_temp is not None and cpu_temp > 70:
        alerts.append("WARNING: CPU temperature is high")

    disk_percent = 0
    try:
        disk_percent = int(disk.replace('%', ''))
    except:
        pass
    if disk_percent > 90:
        alerts.append("ERROR: Disk usage exceeds threshold")

    if service_status != "active":
        alerts.append("CRITICAL: Service failed to start")

    # Also check CPU and Memory for alerts
    if cpu > 50:
        alerts.append("WARNING: CPU usage is above 50%")
    if mem > 70:
        alerts.append("WARNING: Memory usage is above 70%")

    for alert in alerts:
        print(alert)

    return summary, alerts

def main():
    args = parse_args()
    summary, alerts = monitor_system()

    # Save summary JSON if requested
    if args.save_summary:
        path = "summary.json"
        existing = []
        if os.path.exists(path):
            with open(path, "r") as f:
                try:
                    existing = json.load(f)
                except:
                    existing = []
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "summary": summary,
            "alerts": alerts
        }
        existing.append(entry)
        with open(path, "w") as f:
            json.dump(existing, f, indent=4)
        print(f"Summary saved to {path}")

    # Send email if requested and alerts exist
    if args.get_email and alerts:
        body = f"System Monitor Report\n\nSummary:\n"
        for k,v in summary.items():
            body += f"- {k}: {v}\n"
        body += "\nAlerts:\n"
        for alert in alerts:
            body += f"- {alert}\n"
        send_email("🚨 System Alert Report", body, args.recipient)

    # Beep if alerts and beep requested
    if args.get_beep and alerts:
        beep()

if __name__ == "__main__":
    main()
