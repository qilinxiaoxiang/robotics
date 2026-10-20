"""10 Hz A7Z health log for brownout/overheat diagnosis: SoC zone temps, CPU frequency cap and current, load; fsync per line."""
import glob, os, time
zones = sorted(glob.glob("/sys/class/thermal/thermal_zone*"))
names = [open(z + "/type").read().strip() for z in zones]
f = open("/home/radxa/duck-logs/thermal.log", "a")
f.write("# boot %s zones %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S"), names))
while True:
    t = [int(open(z + "/temp").read()) // 100 / 10 for z in zones]
    cur = int(open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq").read()) // 1000
    mx = int(open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq").read()) // 1000
    f.write("%.2f %s cur %d max %d load %s\n" % (time.time(), " ".join("%.1f" % x for x in t), cur, mx, os.getloadavg()[0]))
    f.flush(); os.fsync(f.fileno()); time.sleep(0.1)
