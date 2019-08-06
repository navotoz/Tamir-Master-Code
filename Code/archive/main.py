import datetime
import time
from simulator import Simulator
import rospy
from ros import Ros

tic = datetime.datetime.now()
dofe = 6
ros = Ros()
ros.ter_command("kill -9 " + str(ros.checkroscorerun()))
ros.ros_core_start()
rospy.init_node('arl_python', anonymous=True)
foldere = "combined"
sim = Simulator(dofe, foldere, True)
arms = sim.arms

for i in range(len(arms)/50+1):
    if i == len(arms)/50:
        sim = Simulator(dofe, foldere, False)
        sim.run_simulation(arms[i * 50:], i, len(arms))
    elif i != 0:
        sim = Simulator(dofe, foldere, False)
        sim.run_simulation(arms[i*50:(i+1)*50], i, len(arms))
    else:
        sim.run_simulation(arms[:50], i, len(arms))
    time.sleep(1.5)

toc = datetime.datetime.now()
print('Time of Run (seconds): ' + str((toc - tic).seconds))