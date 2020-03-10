# coding=utf-8
""" Variables: x1 : Joints type - array [Roll, Pitch, Pris]
            x2: Previous axe - array [X, Y, Z]
            x3 : Link Length - array [0.1, 0.4, 0.7]
            x4 : DOF - Int [3, 4, 5, 6]
Objectives:
1)	Min  Degree of Redundancy     [-3:0]
2)	Max  manipulability [0-1]
3)	Min  z (Mid-Range Proximity)
Constrains:
•	Sum (X3) > 1
•	X1[0] = Roll
•	X2[0] = Z
•	X3[0]=0.1
•	No more than 3 Pris in X1
•	If (X1[i]==Roll and X2[i]==Z) than (X1[i+1]!=Roll and X2[i+1]!=Z)
•	Arrival points : reach to one from two upper points and to the middle and bottom points
"""
# from typing import Iterable

# from simulator import simulate
from ros import UrdfClass
from Other import load_json, save_json, pickle_load_data, pickle_save_data, Concepts, MyCsv, get_key
from scipy.spatial import distance
import numpy as np
import copy
from datetime import datetime
from tqdm import tqdm
from time import time
from multiprocessing import Pool
import os
import shutil
np.random.seed(100100)


class Problem:
    def __init__(self, concept_name, confs_of_concepts, confs_results, pop_size=100, parents_number=1, number_of_objects=3,
                 larg_concept=200):
        self.pop_size = pop_size  # size of population
        self.confs_of_concepts = confs_of_concepts  # [x.keys()[0] for x in confs_of_concepts]  # all possible configs names of the concept
        self.confs_results = confs_results  # all the configurations of the concept and their indices
        self.confs_archive = []  # Archive of all the selected configurations
        self.large_concept = len(confs_of_concepts) > larg_concept  # True if large False otherwise
        self.concept_name = concept_name
        self.elit_confs = []
        self.parents_number = parents_number
        self.dof = int(str(concept_name).split(" ")[5].split(",")[0])
        self.stopped = False
        self.number_of_objects = number_of_objects
        self.population = []

    def set_population(self, pop):
        self.population = pop

    def get_population(self):
        return self.population

    def rand_pop(self, pop_size=None):
        """ select random configurations that belongs to the concept
        :param pop_size-[int] the size of selected population - if nothing entred than take self.pop_size
        :return confs- [list]  names of configurations
        """
        if pop_size is None:
            pop_size = self.pop_size
        confs_of_concepts = self.get_configs()
        confs_archive = self.get_prev_confs()
        remain_confs = len(confs_of_concepts) - len(confs_archive)
        # check that the number of selected configuration wont be bigger than the number of remain configurations
        if remain_confs < pop_size:
            pop_size = remain_confs
        num_of_confs = len(confs_of_concepts)
        # select random indices
        indices = np.random.randint(0, num_of_confs, pop_size)
        # get the configurations of the random indices
        random_confs = np.ndarray.tolist(np.asarray(confs_of_concepts)[indices])
        confs = []
        while len(random_confs) != 0:
            for conf in random_confs:
                # if the random configuration in the archive
                if conf in confs_archive:
                    # delete the configuration and select new one
                    random_confs.remove(conf)
                    new_ind = np.random.randint(0, num_of_confs, 1)
                    while new_ind in indices:
                        new_ind = np.random.randint(0, num_of_confs, 1)
                    random_confs.append(confs_of_concepts[new_ind[0]])
                else:
                    confs.append(conf)
                    random_confs.remove(conf)
        return confs

    def evalute(self, pop):
        f1 = []
        f2 = []
        f3 = []
        pops = []
        for p in pop:
            pops.append(p)
            res = self.get_result(p)
            if len(res) == 0:
                f3.append(self.dof)  # dof
                # todo - delete this when adding the simulator
                f2.append(np.around(np.random.normal(0.05, 0.01), 3))    # manipulability
                f1.append(np.around(np.random.normal(0.05, 0.01), 3))
            # check if the configuration allready simulated
            elif res["z"] is not None:
                f3.append(int(res["dof"]))   # dof
                f2.append(1 - float(res["mu"]))  # manipulability
                f1.append(float(res["z"]))   # Mid-Range Proximity
            else:
                f3.append(self.dof)  # dof
                # todo - delete this when adding the simulator
                f2.append(np.around(np.random.normal(0.05, 0.01), 3))    # manipulability
                f1.append(np.around(np.random.normal(0.05, 0.01), 3))  # Mid-Range Proximity
        return [f1, f2, f3, pops, self.concept_name]

    def stop_condition(self):
        """Stop condition of the concept (not of all the problem)
        condition 1 - if all the configuration been checked
        """
        stop = False
        if self.get_prev_confs().shape[0] == self.get_configs().shape[0]:
            stop = True
        return stop

    def archive_elitism(self, new_gen):
        elite_confs = self.get_elite_confs()
        if not elite_confs:
            self.set_elite_confs(new_gen)
            return new_gen
        elite_confs[0].append(new_gen[0][0])
        elite_confs[1].append(new_gen[1][0])
        elite_confs[2].append(new_gen[2][0])
        elite_confs[3].append(new_gen[3][0])
        self.set_elite_confs(elite_confs)
        return elite_confs
        # new_elite_gen = []
        # new_elite_gen_name = []

    def elitism(self, new_gen):
        """Elitism - Make sure the offsprings will be better than the previous generation
        :param new_gen - [list of lists] the results of the last genration
        :return new_elite_gen -[list of lists] the best population from the elite and last offsprings
        """
        elite_confs = self.get_elite_confs()
        if not elite_confs:
            self.set_elite_confs(new_gen)
            return new_gen
        new_elite_gen = []
        new_elite_gen_name = []
        for i in range(self.pop_size):
            for j in range(self.pop_size):
                if elite_confs[0][i] > new_gen[0][j] and elite_confs[1][i] > new_gen[1][j]:
                    new_elite = [new_gen[0][j], new_gen[1][j], new_gen[2][j]]
                    new_elite_gen_name.append(new_gen[3][j])
                    new_gen[0][j] = 100
                    new_gen[1][j] = 100
                    new_elite_gen.append(new_elite)
                    break
            if j == self.pop_size - 1:
                new_elite = [elite_confs[0][i], elite_confs[1][i], elite_confs[2][i]]
                new_elite_gen_name.append(elite_confs[3][i])
                new_elite_gen.append(new_elite)
        new_elite_gen = np.ndarray.tolist(np.asarray(new_elite_gen).T) + [new_elite_gen_name] + [elite_confs[4]]
        self.set_elite_confs(new_elite_gen)
        return new_elite_gen

    @staticmethod
    def assign_fitness(points, dwoi):
        """ calculate the distance from each point to the DWOI
        :param points - [list of lists] the results of last evaluation
        :param dwoi - [list of lists] last Dynamic Window of Intrest
        :return [np array] of the shortest distance form each point to the DWOI
        """
        dwoi_loc = np.asarray(dwoi[:3]).T
        dist = distance.cdist(dwoi_loc,  np.asarray(points[:3]).T, 'euclidean')
        return np.amin(np.around(dist, 3), axis=0)

    @staticmethod
    def selection(dis, num_of_returns=2):
        """Make selection by using RWS return the value
        :param dis: [np array]  distances
        :param num_of_returns:[int] how many elements to return
        :return :[np array] the selected indices that won the RWS
        """
        selected = []
        c = 3.
        fitnes = np.exp(-c*dis)
        fp = np.asarray([i / sum(fitnes) for i in fitnes])
        roullete = np.asarray([sum(fp[:x+1]) for x in range(len(fp))])
        for i in range(num_of_returns):
            wheel = np.random.uniform(0, 1)
            ind = np.where((roullete - wheel) > 0, (roullete - wheel), np.inf).argmin()
            selected.append(round(fitnes[ind], 3))
        return np.abs(np.round(np.log(selected)/c, 3))  # [10-x for x in selected]

    def mating(self, parents, mutation_percent=100):
        """
        :param parents - [list] all the parents that go into the mating pool
        :param mutation_percent - [int] how much mutation wanted
        :return offspring - [list] names of the offsprings
         """
        offspring_size = self.pop_size
        num_mutations = int(offspring_size * mutation_percent/100.)
        num_crossover = offspring_size - num_mutations
        total_attempts = 50  # to prevent infinite loop
        offspring = []
        mut_offspring = 0
        cross_offspring = 0
        for i in range(num_mutations):
            attempt = 0
            in_concept = False
            cross_ok = False
            if mutation_percent == 100:  # if the mutation % is 100 than no crossover
                cross_ok = True
            mut_ok = False
            spring = []
            while not in_concept:
                # select parents randomlly
                j = np.random.randint(0, len(parents))
                k = np.random.randint(0, len(parents))
                parent_1 = np.asarray(Concepts.arm2parts(str(parents[k]).split("_")))
                parent_2 = np.asarray(Concepts.arm2parts(str(parents[j]).split("_")))
                # calculate crossover and mutation and check if they are belongs to the concept
                if not cross_ok and cross_offspring < num_crossover:
                    cross_spring = self.crossover([parent_1, parent_2])
                    cross_conf = self.check_conf(cross_spring) and cross_spring not in offspring
                    if cross_conf:
                        cross_ok = cross_spring not in self.get_prev_confs()
                        spring.append(cross_spring)
                        cross_offspring += 1
                if not mut_ok and mut_offspring < num_mutations:
                    # mut_spring = self.mutation_round(parent_1)
                    mut_spring = self.mutation_rand(parent_1)
                    mut_conf = self.check_conf(mut_spring) and mut_spring not in offspring
                    if mut_conf:
                        mut_ok = mut_spring not in self.get_prev_confs()
                        spring.append(mut_spring)
                        mut_offspring += 1
                in_concept = cross_ok and mut_ok or cross_ok and mut_offspring == num_mutations
                if attempt >= total_attempts:
                    # print("mating problem " + str(i))
                    if len(offspring) > 2*num_mutations-1:
                        spring = self.rand_pop(1)
                        if spring not in offspring:
                            break
                    else:
                        rand_spring = self.rand_pop(2 + abs(len(offspring) - 2*i))
                        for s in rand_spring:
                            if s not in offspring:
                                spring.append(s)
                        if spring:
                            break
                attempt += 1
            for s in spring:
                offspring.append(unicode(s))
        if len(offspring) > offspring_size:
            offspring = offspring[:offspring_size]
        elif len(offspring) < offspring_size:
            print("333333333")
        return offspring

    def crossover(self, parents):
        """ select a random number (link) and all the links&joints&axes until this point
        taken from parent 1 and all the links&joints&axes from this point are taken from parent 2
        :param parents- [list] names of parents
        :return -[str] name of offspring
        """
        dof = self.dof
        for j in range(dof):
            point_of_split = np.random.randint(1, dof)
            child = np.ndarray.tolist(parents[0][:, :point_of_split].copy())
            [child[i].extend(np.ndarray.tolist(parents[1][i, point_of_split:])) for i in range(3)]
            child = to_urdf(child[0], child[1], child[2], "")
            if self.check_conf(child["name"]):
                break
        if j == dof - 1:
            child = np.ndarray.tolist(parents[0])
            child = to_urdf(child[0], child[1], child[2], "")
        return child["name"]

    def mutation_rand(self, parent, nb_prox=1):
        """ switch randomlly 2 links and joints
        :param parent- [np array] names of parents
        :param nb_prox- [int] proximity of the neighboors: 1-first neigboor, 2-second neighboor
        :return -[str] name of offspring
        """
        dof = self.dof
        arm_index = []
        nbs_dict = {1: [[2, 4], [5, 8]], 2: [[1, 5, 8], [4, 7]], 3: [[6, 9], []],
                    4: [[1, 5, 7], [2, 8]], 5: [[2, 4, 8], [1, 7]], 6: [[3, 9], []],
                    7: [[1, 4, 8], [2, 5]], 8: [[2, 5, 7], [1, 4]], 9: [[3, 6], []],
                    11: [[12, 14, 17], [15, 18]], 12: [[11, 15, 18], [14, 17]], 13: [[16, 19], []],
                    14: [[11, 15, 17], [12, 18]], 15: [[12, 14, 18], [11, 17]], 16: [[13, 19], []],
                    17: [[11, 14, 18], [12, 15]], 18: [[12, 15, 17], [11, 14]], 19: [[13, 16], []],
                    21: [[22, 24, 27], [25, 28]], 22: [[21, 25, 28], [24, 27]], 23: [[26, 29], []],
                    24: [[21, 25, 27], [22, 28]], 25: [[22, 24, 28], [21, 27]], 26: [[23, 29], []],
                    27: [[21, 24, 28], [22, 25]], 28: [[22, 25, 27], [21, 24]], 29: [[23, 26], []]
        }
        dict = {'roll z 0.1': 1, 'roll z 0.4': 2, 'roll z 0.7': 3,
                'roll y 0.1': 4, 'roll y 0.4': 5, 'roll y 0.7': 6,
                'roll x 0.1': 7, 'roll x 0.4': 8, 'roll x 0.7': 9,
                'pitch z 0.1': 11, 'pitch z 0.4': 12, 'pitch z 0.7': 13,
                'pitch y 0.1': 14, 'pitch y 0.4': 15, 'pitch y 0.7': 16,
                'pitch x 0.1': 17, 'pitch x 0.4': 18, 'pitch x 0.7': 19,
                'pris z 0.1': 21, 'pris z 0.4': 22, 'pris z 0.7': 23,
                'pris y 0.1': 24, 'pris y 0.4': 25, 'pris y 0.7': 26,
                'pris x 0.1': 27, 'pris x 0.4': 28, 'pris x 0.7': 29
                }
        for p in parent.T:
            arm_index.append(dict["_".join(p).replace("_", " ")])
        ind = np.random.randint(1, dof)
        to_replace = arm_index[ind]
        nbs = nbs_dict[to_replace]
        if nb_prox == 1:
            rand_nb = np.random.choice(nbs[0])
        else:
            rand_nb = np.random.choice(nbs[0] + nbs[1])
        offspring = parent.T
        offspring[ind] = get_key(rand_nb, dict).split(" ")
        offspring = offspring.T
        offspring = to_urdf(offspring[0], offspring[1], offspring[2], "")
        return offspring["name"]

    def mutation_round(self, parent):
        """ Switch the elements in circle. the last will be first first will be second and so on
        :param parent- [np array] names of parents
        :return -[str] name of offspring
        """
        dof = self.dof
        indices = np.concatenate((np.asarray([0, dof-1]), np.arange(1, dof-1)))
        offspring = parent[:, indices]
        offspring = to_urdf(offspring[0], offspring[1], offspring[2], "")
        if offspring["name"][15] == "x":  # for roll\pris x in start
            offspring["name"] = offspring["name"][:15] + "y" + offspring["name"][16:]
        elif offspring["name"][16] == "x":  # for pitch x in start
            offspring["name"] = offspring["name"][:16] + "y" + offspring["name"][17:]
        return offspring["name"]

    @staticmethod
    def confs_by_indices(select, fit):
        """ get the selected distances and return the indices of them if distance appear more
        than once it than take the second item
        :param select - [np array]  the selected fitnesses to find their indices
        :param fit - [np array]  array of the fitness of the configurations
        :return indices - [list]  indices of the selected configuration
         """
        indices = []
        for x in select:
            ind = np.argwhere(fit == x)
            if ind.shape[0] > 1:
                fit[ind[0][0]] = 100
            if len(ind) == 0:
                ind = np.argwhere(np.abs(fit - x) < 0.003)
            try:
                indices.append(ind[0][0])
            except:
                print("ind=" + str(ind) + "  fit=" + str(fit) + "\nx=" + str(x) + "\nselect=" + str(select))
        return indices

    def get_conifgs_by_indices(self, conf_indices):
        """get configuration by indices
        :param conf_indices - [list] indices of the configurations
        :return - [list] - names of the configurations in the selected indices
        """
        get_configs = np.asarray(self.get_configs())
        return np.ndarray.tolist(get_configs[conf_indices])
        # return np.ndarray.tolist(np.unique(get_configs[conf_indices]))

    def check_conf(self, confs):
        """Ceck if the configurations are belongs to the concept
        :param confs: [str] configuration to check if in the concept
        :return :[boolean] True if in the concept False otherwise
        """
        configs = self.get_configs()
        return confs in configs

    # @staticmethod
    # def clost_point(distances, nums_mins=4):
    #     """Find the closest point to the DWOI
    #     :param distances: NxM array-N number of points in the DWOI, M number of points to calc distance
    #     :param nums_mins: number of minimum points to find
    #     :return the index of the closest point
    #     """
    #     indices = []
    #     for i in range(nums_mins):
    #         ind = distances.argmin() % distances.shape[1]
    #         indices.append(ind)
    #         distances[:, ind] = [100] * distances.shape[0]
    #         # distances = distances[:, range(ind) + range(ind + 1, distances.shape[1])]
    #     return indices

    def get_configs(self):
        return self.confs_of_concepts

    def domination_check(self, conf, front):
        """ check if any of the configuration dominated the DWOI and update the DWOI
        :param conf - [list] the results of the configuration
        :param front - [list] the results of the DWOI
        :return front - [list] the new front
        """
        for i, j, k, l in zip(conf[0], conf[1], conf[2], conf[3]):  # z, mu, dof, configuration
            added = False
            for i_front, j_front, k_front, l_front in zip(front[0], front[1], front[2], front[3]):
                # check if the point is dominate the front
                if i <= i_front and j <= j_front and k <= k_front:
                    ind = front[3].index(l_front)
                    del front[0][ind]
                    del front[1][ind]
                    del front[2][ind]
                    del front[3][ind]
                    if front[4] != self.concept_name:
                        del front[4][ind]
                    if not added:
                        front[0].append(i)
                        front[1].append(j)
                        front[2].append(k)
                        front[3].append(l)
                        if front[4] != self.concept_name:
                            front[4].append(self.concept_name)
                        added = True
            if not added:
                front[0].append(i)
                front[1].append(j)
                front[2].append(k)
                front[3].append(l)
                if front[4] != self.concept_name:
                    front[4].append(self.concept_name)
        return front

    def set_prev_confs(self, confs):
        """Add configurtions to the archive """
        self.confs_archive += confs

    def get_prev_confs(self):
        """ Return the configuration in the archive"""
        return self.confs_archive

    def get_result(self, config):
        result = []
        for i in range(len(self.confs_results)):
            if self.confs_results[i].keys()[0] == config:
                result = self.confs_results[i][self.confs_results[i].keys()[0]]
                break
        return result

    def set_elite_confs(self, confs):
        self.elit_confs = confs

    def get_elite_confs(self):
        return self.elit_confs

    def local_stop_condition(self):
        if len(self.get_prev_confs()) == len(self.confs_of_concepts):
            # check if all the configurations simulated
            self.stopped = True


class DWOI:

    def __init__(self, concepts_file="jsons/front_concept", run_time=7):
        self.gen = 0
        self.dwoi = self.dwoi2conf(load_json(concepts_file))  # , self.gen])
        self.stopped = False
        self.start_time = time()
        self.run_time = run_time*3600*24  # in seconds

    def stop_condition(self):
        if self.run_time <= time() - self.start_time:
            self.stopped = True

    def set_dwoi(self, dwoi):
        for i in range(len(dwoi[3])):
            if type(dwoi[3][i]) != unicode:
                dwoi[3][i] = unicode(dwoi[3][i][0])
        self.dwoi.append(dwoi)

    def get_all_dwoi(self):
        return self.dwoi

    def get_last_dwoi(self):
        return self.dwoi[-1][:]

    @staticmethod
    def dwoi2conf(dwoi):
        """ conf from the following format: 4D list:
        0 - list of z
        1 - list of mu
        2 - list of dof
        3 - list of configurations names
        4 - concept
        5 - number of gen
        """
        conf = [[], [], [], [], []]  # , dwoi[1]]
        for w in dwoi:
            conf[0].append(w["z"])
            conf[1].append(w["mu"])
            conf[2].append(w["dof"])
            conf[3].append(w["configuration"])
            conf[4].append(w["concept"])
        return [conf]

    def set_gen(self, gen):
        self.gen = gen

    def get_gen(self):
        return self.gen


def to_urdf(interface_joints, joint_parent_axis, links, folder):
    """Create the desired confiuration
    :param interface_joints- [list] roll,pitch or prismatic (roll -revolute around own Z axis,
                                    pitch - revolute that not roll,  pris - prismatic along z)
    :param links -[list] length of links
    :param joint_parent_axis - [list] the axe, in the parent frame, which each joint use
    :param folder - [str] where the urdf saved - not in use
    :return -[dict] -contain the configuration name and all the data to the urdf file
        """
    joints = []
    joint_axis = []
    rpy = []
    # file_name = os.environ['HOME'] + "\Tamir_Ws\src\manipulator_ros\Manipulator\man_gazebo\urdf\"
    # + str(dof) + "dof\combined\"
    file_name = ""
    rolly_number = -1
    pitchz_number = 1
    prisy_number = -1
    for i in range(len(joint_parent_axis)):
        # file_name += interface_joints[i].replace(" ", "") + "_" + joint_parent_axis[i].replace(" ", "") + "_" + \
        #              links[i].replace(".", "_")
        file_name += interface_joints[i] + "_" + joint_parent_axis[i] + "_" + str(links[i]).replace(".", "_")
        if interface_joints[i] == "roll":
            joints.append("revolute")
            joint_axis.append('z')
            if joint_parent_axis[i] == "y":
                rolly_rot = '${' + str(rolly_number) + '/2*pi} '
                rpy.append([rolly_rot, '0 ', '0 '])
                rolly_number = rolly_number * -1
            elif joint_parent_axis[i] == "x":
                rpy.append(['0 ', '${pi/2} ', '0 '])
            elif joint_parent_axis[i] == "z":
                rpy.append(['0 ', '0 ', '0 '])
        elif interface_joints[i] == "pitch":
            joints.append("revolute")
            joint_axis.append('y')
            if joint_parent_axis[i] == "y":
                rpy.append(['0 ', '0 ', '0 '])
            elif joint_parent_axis[i] == "x":
                rpy.append(['0 ', '0 ', '${-pi/2} '])
            elif joint_parent_axis[i] == "z":
                # rpy.append(['${pi/2} ', '0 ', '0 '])
                pitchz = '${' + str(pitchz_number) + '/2*pi} '
                rpy.append([pitchz, '0 ', '0 '])
                pitchz_number = pitchz_number * -1
        elif interface_joints[i] == "pris":
            joints.append("prismatic")
            joint_axis.append('z')
            if joint_parent_axis[i] == "y":
                # rpy.append(['${pi/2} ', '0 ', '0 '])
                prisy = '${' + str(prisy_number) + '/2*pi} '
                rpy.append([prisy, '0 ', '0 '])
                prisy_number = prisy_number * -1
            elif joint_parent_axis[i] == "x":
                rpy.append(['0 ', '${-pi/2} ', '0 '])
            elif joint_parent_axis[i] == "z":
                rpy.append(['0 ', '0 ', '0 '])
    arm = UrdfClass(links, joints, joint_axis, rpy)
    # arm.urdf_write(arm.urdf_data(), file_name)
    return {"arm": arm, "name": file_name, "folder": folder}


def set_pop_size(num_concept_confs, min_configs=None):
    """decide the population size: going to be the bigger between min_configs[1] % of concepts number or min_configs[0]
     :param num_concept_confs: [int] number of configurations in this concept
     :param min_configs: [2 elements list] the limits: min_configs[0] is the minimum number of the population
                        min_configs[1] is the percent of number of configurations in the concept
    :return pop_size: [int] size of the pipulation
     """
    if min_configs is None:
        min_configs = [1, 0]
    if num_concept_confs * min_configs[1] / 100 > min_configs[0]:
        pop_size = num_concept_confs * min_configs[1] / 100
    else:
        pop_size = min_configs[0]
    return pop_size


def init_concepts(larg_concept=1500, arm_limit=None, parents_number=1):
    """ Initilize all the concept and the first populations
    :param larg_concept: [int] minimum number of configurations in concept in order to concept will be large
    :param arm_limit: [2 elements list] the limits: arm_limit[0] is the minimum number of the population
            arm_limit[1] is the percent of number of configurations in the concept
    :param parent_percent: [int] how much from the populatoin will be parents
    :return prob - [list of objects] all the data of each concept
    """
    if arm_limit is None:
        arm_limit = [1, 0]
    # load all the concepts
    concepts_with_conf, confs_results = get_prev_data()
    prob = []
    # population = []
    for i in range(len(concepts_with_conf)):
        # Initiliaze each concept
        name_of_concept = list(concepts_with_conf)[i]
        number_of_arms = set_pop_size(len(concepts_with_conf[name_of_concept]), arm_limit)
        prob.append(Problem(name_of_concept, concepts_with_conf[name_of_concept], confs_results[name_of_concept], parents_number=parents_number,
                            pop_size=number_of_arms, larg_concept=larg_concept))
        # initiliaze population
        prob[i].set_population(prob[i].rand_pop())
        # population.append(prob[i].rand_pop())
    return prob  # , population


def get_prev_data(all_concepts_json="jsons/concepts+configs+results", ga_json="jsons/concepts2ga"):
    """ get all the previous data and the concepts to enter into the ga and return only the relevant data
    :param all_concepts_json - [str] json file with all the simulated data
    :param ga_json - [str] all the concepts to check in the GA
    :return ga_data- dictoinary with all the configurations and there results per concept
    """
    all_concepts = load_json(all_concepts_json)
    ga_concepts = load_json(ga_json)
    ga_data = {}
    for k in ga_concepts:
        if k in all_concepts:
            ga_data[k] = all_concepts[k]
    return ga_concepts, ga_data


def csvs2data():
    """ Take all the created CSVs and insert them into one variable
     :return data -[list of dicts] the results of all the simulated configuration in this run
     """
    data = []
    for file_csv in os.listdir(os.getcwd()):
        if file_csv.endswith(".csv"):
            data.append(MyCsv.load_csv(file_csv[:-4]))
    data = [val for sublist in data for val in sublist]
    return data


def set_new_data(all_concepts_json="jsons/concepts+configs+results", ga_json="jsons/concepts2ga"):
    """ get all the previous data and the concepts to enter into the ga and return only the relevant data
    :param all_concepts_json - [str] json file with all the simulated data
    :param ga_json - [str] all the concepts to check in the GA
    """
    data = csvs2data()
    jsons_folder = os.environ['HOME'] + "/Tamir/Master/Code/"
    all_concepts_json = jsons_folder + all_concepts_json
    ga_json = jsons_folder + ga_json
    all_concepts = load_json(all_concepts_json)
    ga_concepts = load_json(ga_json)
    for dat in data:
        second_loop_stop = False
        for con in ga_concepts:
            k = 0
            for concept in all_concepts[con]:
                if dat["name"] in concept:
                    second_loop_stop = True
                    if all_concepts[con][k][dat["name"]]["mu"] is not None:
                        print("Check it!!!")
                    all_concepts[con][k] = {unicode(dat["name"]): {"mu": dat["mu"], "z": dat["Z"], "dof": dat["dof"],
                                                                  "name": unicode(dat["name"])}}
                    break
                k += 1
            if second_loop_stop:
                break
    save_json(all_concepts_json + "new", all_concepts, "w+")
    # pickle_save_data(all_concepts, all_concepts_json + "new")


def move_folder(src_folder_name="urdf/6dof/", dst_folder_name=""):
    if not dst_folder_name:
        dst_folder_name = os.environ['HOME'] + \
                          "/Tamir_Ws/src/manipulator_ros/Manipulator/man_gazebo/urdf/6dof/combined/"
    if os.path.exists(dst_folder_name):
        shutil.rmtree(dst_folder_name)
    shutil.move(src_folder_name, dst_folder_name)


def check_exist(problem):
    """ return which urdfs to create for simulation
    :param problem: [object] of specific concept
    :return to_sim: [list] names of urdfs to create
    """
    pop = problem.get_population()
    to_sim = []
    for p in pop:
        res = problem.get_result(p)
        # check if the configuration allready simulated
        if len(res) == 0:
            to_sim.append(p)
        elif res["z"] is None:
            to_sim.append(p)
    return to_sim


def new_data(prob):
    """ update each concept results agter the simulation
    :param prob - [list of objects] the data of all the objects
    :return prob - [list of objects] updated data of all the objects
    """
    data = MyCsv.load_csv("results_file" + datetime.now().strftime("%d_%m_") + "6dof_4d_")
    for dat in data:
        k = 0
        outer_loop_stop = False
        for con in prob:
            j = 0
            for c in con.confs_results:
                if dat["name"] == c.keys()[0]:
                    outer_loop_stop = True
                    prob[k].confs_results[j][prob[k].confs_results[j].keys()[0]] = {"mu": dat["mu"],
                                                    "z": dat["Z"], "dof": dat["dof"], "name": unicode(dat["name"])}
                    break
                j += 1
            k += 1
            if outer_loop_stop:
                break
    return prob


def sim(prob):
    print("start creating urdfs")
    # configurations to create urdf
    to_sim = []
    con = Concepts()
    k = 0
    for p in prob:
        to_sim.append(check_exist(p))
        k += 1
        if k == 10:
            break
    # create urdf files
    con.create_files2sim(filter(None, to_sim))
    # move the files into the desired place
    # move_folder()
    print("start simulating")
    # simulate()
    # prob = new_data(prob)
    return prob


def run(prob):
    global woi
    # check if the local stop condition applied
    if prob.stopped:
        return []
    population = prob.get_population()
    # insert previous configurations into archive
    prob.set_prev_confs(population)
    # Evaluation
    confs_results = prob.evalute(np.asarray(population))
    # Update DWOI if necessary
    front = prob.domination_check(confs_results, copy.deepcopy(woi.get_last_dwoi()))
    if front != woi.get_last_dwoi():
        woi.set_dwoi(front)
    # Stop Condition
    prob.local_stop_condition()
    # Check if large concept
    if prob.large_concept:  # if large concept
        # elitism
        # confs_results_elite = prob.elitism(confs_results)
        confs_results_elite = prob.archive_elitism(confs_results)
        # Assign fitness
        fitness = prob.assign_fitness(confs_results_elite, woi.get_last_dwoi())  # calc minimum distance for each config
        # Selection (RWS)
        selection = prob.selection(fitness, prob.parents_number)
        selected_confs_ind = prob.confs_by_indices(selection, fitness)
        selected_confs = prob.get_conifgs_by_indices(selected_confs_ind)
        # Mating
        population = prob.mating(selected_confs)
    else:  # if small concept
        # Random Selection
        population = prob.rand_pop()
    prob.set_population(population)
    return prob


if __name__ == '__main__':
    # ## Setting parameters
    run_tim = 7  # how many dats to run
    num_gens = 10  # how many gens to run
    parents_number = 1  # number of parents
    large_concept = 1000  # define what is a large concept
    arms_limit = [1, 0]  # population limit: arms_limit[0]: minimum number of configs, arms_limit[1]: % of population
    threads = 1  # how many threads to use if using parallel
    name = "optimizaion_WOI"  # the name of the json file of the DWOI - saved every gen
    params = "Number of gens: " + str(num_gens) + "\nparents_number: " + str(parents_number) + \
             "\nLarge concept:" + str(large_concept) + "\nRun Time (days): " + str(run_tim) +  \
             "\nNumber of Threads used: " + str(threads)
    # enter all the results to one folder
    results_folder = "opt_results/" + datetime.now().strftime("%d_%m") + "-0"
    while os.path.isdir(results_folder):
        results_folder = results_folder[:-1] + str(int(results_folder[-1]) + 1)
    os.mkdir(results_folder)
    os.mkdir(results_folder + "/urdf")
    print(results_folder + " folder created \nStart Optimization")
    with open(results_folder + "/parameters.txt", "w+") as f:
        f.write(params)
        f.close()
    # load the first WOI
    woi = DWOI(run_time=run_tim)
    # Initilize all the concepts GA
    print("initiliaze data")
    probs = init_concepts(larg_concept=large_concept, arm_limit=arms_limit, parents_number=parents_number)
    # change the working dir
    os.chdir(results_folder)
    try:
        # decide how many threads to use
        # with Pool(threads) as p:
        # running each generation
        for n in (range(num_gens)):
            # simulate the population
            probs = sim(prob=probs)
            # Save the current WOI
            save_json(name, [{"gen_" + str(woi.get_gen()): woi.get_last_dwoi()}])
            print("Generation " + str(n + 1) + " of " + str(num_gens) + " generations")
            for t in tqdm(range(1)):  # len(probs)
                probs[t] = run(probs[5])
            # probs = list(tqdm(p.imap(run, probs), total=len(probs)))
            # Update generation
            woi.set_gen(n + 1)
            # Check global stop condition
            woi.stop_condition()
            if woi.stopped:
                break
    finally:
        print("Saving data...")
        # p.close()
        save_json(name, [{"gen_" + str(woi.get_gen()): woi.get_last_dwoi()}])
        # pickle_save_data(woi, "woi")
        # pickle_save_data(probs, "problems")
        # set_new_data()
        print("Finished")



# done - create main results file
# done - save dwoi to json every iteration?
# done - check that DWOI archive change only after change
# done - add elitism check
# done - set each concept relative numbers of arms (init concepts)
# done - parents number to each concept
# todo - in mating- if doesnt succeeded to create offspring?
# done - set json file with the desired concepts
# done - how to evalute?  run simulation for all ?
# done - how to get the results from the simulator
# done - to check from main results file if allready simulated
# done - check the differences with parallel - doesnt share global vars - need to change the code

# nottodo- play with the follow parameters: mutation rate, parents number, number of offsprings
# to?do - take a concept with ~10000 conf and fully simulate him
