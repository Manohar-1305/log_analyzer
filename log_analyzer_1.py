import os
import platform
import argparse
from datetime import datetime
import json
import smtplib
from email.mime.text import MIMEText
from collections import Counter
import subprocess

def parse_args():
    parser = argparse.ArgumentParser(description="Log Analyzer CLI Tool")
    parser.add_argument('-f', '--file', type=str, required=True, help="Path to log file")
    parser.add_argument('-k', '--keywords', type=str, nargs='+',
                        default=["warn", "critical", "error", "fail"],
                        help="Keywords to search for")
    parser.add_argument('--save-summary', action='store_true', help="Save summary to JSON")
    parser.add_argument('--get-beep', action='store_true', help="Beep if alert keywords found")
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

def monitor_system():
    os.makedirs("logs", exist_ok=True)
    time_stamp = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    log_file = f"logs/monitor_{datetime.now().strftime('%d-%m-%Y')}.log"

    # CPU Usage
    cpu_usage = subprocess.getoutput("top -bn1 | grep 'Cpu(s)' | awk '{print $2 + $4}'")

    # Memory Usage
    mem_cmd = "free -m | grep 'Mem' | awk '{print (($3-$6)/$2)*100}'"
    mem_usage = subprocess.getoutput(mem_cmd)

    # Disk Usage
    disc_usage = subprocess.getoutput("df -h / | awk 'NR==2{print $5}'")

    # Load Average
    load_avg = subprocess.getoutput("uptime | awk -F'load average:' '{print $2}'")

    # Uptime
    uptime = subprocess.getoutput("uptime -p")

    with open(log_file, "a") as f:
        f.write(f"[{time_stamp}] CPU: {cpu_usage} | RAM: {mem_usage} | Disc: {disc_usage} | LoadAvg: {load_avg} | Up Time: {uptime}\n")
        f.write(f"[{time_stamp}] Top 5 Memory Consuming Processes:\n")
        top_mem = subprocess.getoutput("ps -aux --sort=-%mem | awk 'NR<=6{printf \"%s\\t%s\\t%s\\t%s\\n\", $1, $2, $4, $11}'")
        f.write(top_mem + "\n")

    print(f"CPU Usage: {cpu_usage}%")
    print(f"Memory Usage: {mem_usage}%")
    print(f"Disk Usage: {disc_usage}")
    print(f"Uptime: {uptime}")
    print(f"Load Average: {load_avg}")
    print("Top 5 Memory Consuming Processes:")
    print(top_mem)

def analyze_logs(args):
    alert_keywords = ["warn", "fail", "critical", "error"]
    counts = Counter()

    try:
        with open(args.file, "r") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"❌ Error reading log file: {e}")
        return

    for line in lines:
        for keyword in args.keywords:
            if keyword.lower() in line.lower():
                counts[keyword] += 1

    total = sum(counts.values())
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_summary = {
        "timestamp": timestamp,
        "log_file": args.file,
        "summary": {}
    }

    print("\n🔍 Log Summary:")
    for keyword in args.keywords:
        count = counts[keyword]
        percent = ((count / total) * 100) if total > 0 else 0
        bar = "#" * (int(percent) // 4)
        print(f"{keyword.capitalize():<10}: {count} | {bar} ({percent:.1f}%)")
        log_summary["summary"][keyword] = {
            "count": count,
            "percentage": f"{percent:.1f}% {bar}"
        }

    # Save JSON summary
    if args.save_summary:
        path = "summary.json"
        existing = []
        if os.path.exists(path):
            with open(path, "r") as f:
                try:
                    existing = json.load(f)
                except:
                    existing = []
        existing.append(log_summary)
        with open(path, "w") as f:
            json.dump(existing, f, indent=4)

    # Email summary even if all counts are 0
    if args.get_email:
        body = f"📄 Log File: {args.file}\n🕒 Timestamp: {timestamp}\n\n📊 Summary:\n"
        for k, v in log_summary["summary"].items():
            body += f"- {k.capitalize()}: {v['count']} ({v['percentage']})\n"
        send_email("🚨 Log Summary Report", body, args.recipient)

    # Trigger beep if any alert keyword found
    if args.get_beep:
        if any(counts[k] > 0 for k in alert_keywords):
            print("\n⚠️ ALERT: Beep due to alert keyword match")
            beep()

def main():
    args = parse_args()
    monitor_system()
    analyze_logs(args)

if __name__ == "__main__":
    main()
