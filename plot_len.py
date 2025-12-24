import csv
import matplotlib.pyplot as plt

LOG_PATH = "experiments/dmc_result/guandan/logs.csv"

frames = []
returns = {0: [], 1: [], 2: [], 3: []}

with open(LOG_PATH, newline="") as f:
    lines = f.readlines()

# 第一行是 "# header"，去掉 "# "
header = lines[0].lstrip("# ").strip().split(",")
data_lines = lines[1:]

reader = csv.DictReader(data_lines, fieldnames=header)

for row in reader:
    frames.append(int(float(row["frames"])))
    for p in returns:
        returns[p].append(float(row[f"mean_episode_length_{p}"]))

plt.figure()
for p, vals in returns.items():
    plt.plot(frames, vals, label=f"player {p}")

plt.xlabel("Frames")
plt.ylabel("Mean Episode Length")
plt.title("DMC Guandan Training Curve")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
