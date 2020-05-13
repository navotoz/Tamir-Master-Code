from Other import save_json, load_json, plot_cr, plot_woi, fix_json
import os
import pickle
import matplotlib.pyplot as plt
from matplotlib import animation
import numpy as np
from tqdm import tqdm
from optimization import Problem
from scipy.spatial import distance
import copy
from hv import HyperVolume
from scipy.stats import wilcoxon
import itertools
from statistics import variance
import math
from mpl_toolkits.axes_grid1.axes_divider import make_axes_locatable
from scipy import stats


def run_results(prob, gen_num=1, elite_archive=True):
    scores = []
    for i in range(gen_num):
        scores.append([])
    elites = []
    gen_num_old = gen_num
    for b in prob:
        gen_num = gen_num_old
        if elite_archive:
            if b.elit_confs_archive[0][0] != 1.0:
                elites.append(b.elit_confs_archive)
        else:
            if b.elit_confs[0][0] != 1.0:
                elites.append(b.elit_confs)
        if gen_num >= len(b.confs_archive):
            gen_num = len(b.confs_archive)
        conf = b.confs_archive[:gen_num]
        res = b.confs_results
        for r in res:
            for c in range(gen_num):
                if len(conf) < gen_num:
                    continue
                if r.keys()[0] == conf[c]:
                    if float(r[conf[c]]["z"]) == 2.0 or float(r[conf[c]]["z"]) == 1.0:
                        # continue
                        r[conf[c]]["z"] = "0.5"
                        r[conf[c]]["mu"] = "0"
                    scores[c].append([float(r[conf[c]]["z"]), 1 - float(r[conf[c]]["mu"])])
                    continue
    return scores, elites


def calc_dis(elite):
    # elite = mut_a[i][1][0][j]
    dis_a_min = 1.5
    for k in range(len(elite[0])):
        dis_a = distance.euclidean((elite[0][k], elite[1][k]), (0, 0))
        if dis_a < dis_a_min:
            dis_a_min = dis_a
    return dis_a_min


def mutation_check(ami,  tamir, comb):
    folder_name = os.getcwd() + ami
    folder_name_t = os.getcwd() + tamir
    folder_name_c = os.getcwd() + comb
    with open(folder_name+"problems.pkl") as f:
        a = pickle.load(f)
    with open(folder_name_t+"problems.pkl") as f:
        t = pickle.load(f)
    with open(folder_name_c + "problems.pkl") as f:
        c = pickle.load(f)
    mut_a = []
    mut_t = []
    mut_c = []
    for i in tqdm(range(6)):
        mut_a.append(run_results(a[i:i+1], 1240))
        mut_t.append(run_results(t[i:i+1], 1240))
        mut_c.append(run_results(c[i:i+1], 1240))
    delta = 1
    plt.ioff()
    # plt.figure(figsize=(24.0, 10.0)).canvas.set_window_title('Cr')
    fig, axs = plt.subplots(6, 1, figsize=(24, 10), facecolor='w', edgecolor='k')
    plt.subplots_adjust(left=0.05, bottom=0.07, right=0.99, top=0.99)
    for i in tqdm(range(len(a))):
        distances_a = [[], [], [], [], [], []]
        distances_t = [[], [], [], [], [], []]
        distances_c = [[], [], [], [], [], []]
        for j in range(0, 1240, delta):
            if mut_a[i][0][j]:
                elite = mut_a[i][1][0][j]
                dis_a_min = calc_dis(elite)
                distances_a[i].append(dis_a_min)
            if mut_t[i][0][j]:
                elite = mut_t[i][1][0][j]
                dis_t_min = calc_dis(elite)
                distances_t[i].append(dis_t_min)
            if mut_c[i][0][j]:
                elite = mut_c[i][1][0][j]
                dis_c_min = calc_dis(elite)
                distances_c[i].append(dis_c_min)
        axs[i].scatter(range(len(distances_a[i])), distances_a[i], color="b", marker="^", label="Ami mutation")
        axs[i].scatter(range(len(distances_t[i])), distances_t[i], color="k", marker="*", label="Tamir mutaion ")
        axs[i].scatter(range(len(distances_c[i])), distances_c[i], color="r", marker="+", label="comobined mutation")
        axs[i].legend(loc="best")
        axs[i].set_xticks(np.arange(0, 1240, step=40))
        axs[i].set_xlim(0)
        axs[i].set_ylim(0)
    plt.xlabel("Generations", fontsize=26)
    axs[3].set_ylabel("Distance to Origin", fontsize=26)
    plt.show()


def first_gen_and_elite_res(name="/opt_results/22_04_tamir_mut/"):
    folder_name = os.getcwd() + name
    with open(folder_name+"problems.pkl") as f:
        a = pickle.load(f)
    gen_nums = 1
    d, e = run_results(a, gen_nums, elite_archive=False)
    save_json(folder_name + "first_gen_res", d, "w+")
    save_json(folder_name + "elits", e, "w+")
    b = load_json(folder_name + "elits")


def domination_check(conf, front, concept_name):
    """ check if any of the configuration dominated the DWOI and update the DWOI
    :param conf - [list] the results of the configuration
    :param front - [list] the results of the DWOI
    :return front - [list] the new front
    """
    for i, j, k, l in zip(conf[0], conf[1], conf[2], conf[3]):  # z, mu, dof, configuration
        if i == -1.0 or i == -1 or i == -70.0 or i == -70:
            continue
        added = False
        point_dominated = False
        for i_front, j_front, k_front, l_front in zip(front[0], front[1], front[2], front[3]):
            # check if the point is dominate the front
            if i <= i_front and j <= j_front and k <= k_front:
                ind = front[3].index(l_front)
                del front[0][ind]
                del front[1][ind]
                del front[2][ind]
                del front[3][ind]
                if front[4] != concept_name:
                    del front[4][ind]
                if not added:
                    front[0].append(i)
                    front[1].append(j)
                    front[2].append(k)
                    front[3].append(l)
                    if front[4] != concept_name:
                        front[4].append(concept_name)
                    added = True
            # check if front dominate the point
            elif i >= i_front and j >= j_front and k >= k_front:
                point_dominated = True
                break
        if not (added or point_dominated):
            front[3].append(l)
            front[0].append(i)
            front[1].append(j)
            front[2].append(k)
            if front[4] != concept_name:
                front[4].append(concept_name)
    # print(front)
    return front


def no_woi_front(elites):
    front = elites[0]
    concepts = []
    for i in range(len(front[0])):
        concepts.append(front[4])
    front[4] = concepts
    for elite in elites[1:]:
        front = domination_check(elite, front, elite[4])
    return front


def woi_comprasion(names=["/results/mutauioncheck/22_04_tamir_mut/"]):
    labels = ["Tamir_mut", "Ami_mut", "Rand_mut", "pre_DWOI", "Best_DWOI", "Com_mut"]
    # labels = ["Vm1", "Vm2", "Vm3", "pre_DWOI", "Best_DWOI"]
    tit = names[0].split("/")[4] + " WOI comparison"
    save_folder = "/".join(names[0].split("/")[:4])
    folder_name = os.getcwd() + "/results/mutauioncheck/"
    t = load_json(os.getcwd() + names[1] + "woi_last")
    pre_woi = copy.deepcopy(t["dwoi"][0])
    t_woi = load_json(os.getcwd() + names[1] + "elits")
    t_woi = no_woi_front(t_woi)
    a_woi = load_json(os.getcwd() + names[0] + "elits")
    a_woi = no_woi_front(a_woi)
    c_woi = load_json(os.getcwd() + names[3] + "elits")
    c_woi = no_woi_front(c_woi)
    r_woi = load_json(os.getcwd() + names[2] + "elits")
    r_woi = no_woi_front(r_woi)
    all_points =[[], [], [], [], [], []]   # [[]] * 220  #
    k = 0
    concepts_names = []
    with open(folder_name+"problems.pkl") as f:
        problems = pickle.load(f)
    front = copy.deepcopy([pre_woi[1], pre_woi[0], pre_woi[2], pre_woi[3],  pre_woi[4]])
    d = []
    for prob in problems:
        for res in prob.confs_results:
            conf = [[1-float(res[res.keys()[0]]["mu"])], [float(res[res.keys()[0]]["z"])],
                    [float(res[res.keys()[0]]["dof"])], [res[res.keys()[0]]["name"]]]
            front = domination_check(conf, front, prob.concept_name)
            if conf[0][0] == 71 or conf[1] == 70 or conf[0][0] == 2.0 or conf[1] == 2.0:
                conf[0] = [1]
                conf[1] = [0.5]
            d.append(conf[0][0])
            all_points[k].append([conf[0][0], conf[1][0]])
        all_points[k] = np.asarray(all_points[k], dtype=float).T
        concepts_names.append(prob.concept_name)
        k += 1
    plt.figure(figsize=(24.0, 10.0)).canvas.set_window_title(tit)
    plt.subplots_adjust(left=0.07, bottom=0.05, right=0.98, top=0.95)
    x = [[], [], [], [], [], []]
    y = [[], [], [], [], [], []]
    for xt, yt, dt in zip(t_woi[0], t_woi[1], t_woi[2]):
        if dt == 6 or dt == 6.0:
           x[0].append(xt)
           y[0].append(yt)
    for xa, ya, da in zip(a_woi[0], a_woi[1], a_woi[2]):
        if da == 6 or da == 6.0:
            x[1].append(xa)
            y[1].append(ya)
    for xc, yc, dc in zip(c_woi[0], c_woi[1], c_woi[2]):
        if dc == 6 or dc == 6.0:
            x[5].append(xc)
            y[5].append(yc)
    for xr, yr, dr in zip(r_woi[0], r_woi[1], r_woi[2]):
        if dr == 6 or dr == 6.0:
            x[2].append(xr)
            y[2].append(yr)
    for xp, yp, dp in zip(pre_woi[0], pre_woi[1], pre_woi[2]):
        if dp == 6 or dp == 6.0:
            x[3].append(xp)
            y[3].append(yp)
    for xf, yf, df in zip(front[1], front[0], front[2]):
        if df == 6 or df == 6.0:
            x[4].append(xf)
            y[4].append(yf)
    colors = ["b", "k", "r", "g", "orange", "cyan"]
    shapes = ["*", "^", ">", "8", ".", "<"]
    for i in range(6):
        a = np.asarray([x[i], y[i]])
        inds = np.argsort(a[0])
        x[i] = a[0, inds]
        y[i] = a[1, inds]
        plt.plot(x[i], y[i], color=colors[i], marker=shapes[i], label=labels[i])
    for conc_points, label in zip(all_points,concepts_names):
        x = conc_points[1]
        y = conc_points[0]
        plt.scatter(x, y, alpha=0.1, s=60)
    plt.xlabel("Mid Proximity", fontsize=20)
    plt.ylabel("1 - Manipulability Index", fontsize=20)
    plt.title("WOI Comparison", fontsize=26)
    plt.legend(fontsize=10)
    plt.grid(True)
    # plt.show()
    plt.savefig(os.getcwd() + save_folder + "/" + tit)
    plt.close()


def all_points():
    folder_name = os.getcwd() + "/results/mutauioncheck/"
    all_points =[[], [], [], [], [], []]
    k = 0
    concepts_names = []
    with open(folder_name+"problems.pkl") as f:
        problems = pickle.load(f)
    d = []
    for prob in problems:
        for res in prob.confs_results:
            conf = [[1-float(res[res.keys()[0]]["mu"])], [float(res[res.keys()[0]]["z"])],
                    [float(res[res.keys()[0]]["dof"])], [res[res.keys()[0]]["name"]]]
            if conf[0][0] == 71 or conf[1] == 70 or conf[0][0] == 2.0 or conf[1] == 2.0:
                conf[0] = [1]
                conf[1] = [0.5]
            d.append(conf[0][0])
            all_points[k].append([conf[0][0], conf[1][0]])
        all_points[k] = np.asarray(all_points[k], dtype=float).T
        concepts_names.append(prob.concept_name)
        k += 1
    return all_points, concepts_names


# For animation
def init_lines():
    for line in lines:
        line.set_data([],[])
    return lines


def animate_lines(o):
    i = o * d + d
    colors = ["b", "r", "k", "cyan"]
    for j, line in enumerate(lines):
        x = []
        y = []
        for p in range(len(woi[j][i % 1240])):
            x.append(woi[j][i % 1240][p][0])
            y.append(woi[j][i % 1240][p][1])
        line.set_data(x, y)
        line.set_label(labels[j])
        line.set_color(colors[j])
    ttl.set_text("Generation: " + str(i))
    plt.legend()
    return lines


def add_data(t):
        wo = []
        for k in range(len(t)):
            wo.append([])
            woi = np.asarray(t[k][t[k].keys()[0]][:3])
            inds = np.argsort(woi[0])
            woi[0] = woi[0, inds]
            woi[1] = woi[1, inds]
            woi[2] = woi[2, inds]
            for j in range(len(woi[2])):
                if woi[2][j] == 6.0 or woi[2][j] == 6:
                    wo[k].append([woi[0][j], woi[1][j]])
        if len(wo) < 1240:
            for t in range(len(wo), 1240):
                wo.append(wo[-1])
        return wo


def plot_init_woi():
    x = []
    y = []
    for k in range(len(woi[0][0])):
        x.append([woi[0][0][k][0]])
        y.append([woi[0][0][k][1]])
    plt.plot(x, y, label="Initial DWOI", color="g")


def woi_comprasion_all(names=["/results/mutauioncheck/22_04_tamir_mut/"]):
    tit = names[0].split("/")[6] + " WOI comparison"
    save_folder = "/".join(names[0].split("/")[:6])
    woi = []
    for name in names:
        woi.append(no_woi_front(load_json(os.getcwd() + name + "elits")))
    plt.ioff()
    plt.figure(figsize=(24.0, 10.0)).canvas.set_window_title(tit)
    plt.subplots_adjust(left=0.07, bottom=0.05, right=0.98, top=0.95)
    x = []
    y = []
    for i, w in enumerate(woi):
        x.append([])
        y.append([])
        for xt, yt, dt in zip(w[0], w[1], w[2]):
            if dt == 6 or dt == 6.0:
               x[i].append(xt)
               y[i].append(yt)
    for i in range(len(x)):
        a = np.asarray([x[i], y[i]])
        inds = np.argsort(a[0])
        x[i] = a[0, inds]
        y[i] = a[1, inds]
        plt.plot(x[i], y[i])
    plt.xlabel("Mid Proximity", fontsize=20)
    plt.ylabel("1 - Manipulability Index", fontsize=20)
    plt.title("WOI Comparison", fontsize=26)
    # plt.legend(fontsize=10)
    plt.grid(True)
    # plt.show()
    plt.savefig(os.getcwd() + save_folder + "/" + tit)
    plt.close()
    return x, y


def plot_wilcoxon(volumes, medians_v, variance_v, labels, titl="Hyper Volume"):
    fig = plt.figure(figsize=(24.0, 10.0))
    fig.canvas.set_window_title(titl)
    plt.subplots_adjust(left=0.03, bottom=0.17, right=0.98, top=0.95)
    grid = plt.GridSpec(1, 3, wspace=0.2)
    ax = fig.add_subplot(grid[0, :-1])
    wil = np.zeros((len(volumes), len(volumes)))
    for i in range(len(volumes)):
        for j in range(i+1, len(volumes)):
            # _, p_value = wilcoxon(volumes[i], volumes[j])
            _, p_value = stats.ranksums(volumes[i], volumes[j])
            wil[i, j] = p_value * 100
            wil[j, i] = p_value * 100
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size='5%', pad=0)
    fig.colorbar(ax.matshow(wil),cax)
    tex = []
    for i, x in enumerate(wil):
        tex.append([])
        for j, y in enumerate(x):
            tex[i].append(str(y))
            ax.text(i,j, str(round(y, 2)), va='center', ha='center', color="white")
    ax.set_xticks(np.arange(16))
    ax.set_yticks(np.arange(16))
    ax.set_xticklabels(labels, rotation="vertical")
    ax.xaxis.set_ticks_position('bottom')
    ax.set_yticklabels(labels)
    ax.set_title("Wilcoxon", y=1, fontsize=24)
    ax = fig.add_subplot(grid[0, -1])
    ax.errorbar(labels, medians_v, yerr=variance_v, ecolor='k', fmt=".r")
    ax.set_xticks(np.arange(len(medians_v)))
    ax.set_xticklabels(labels, rotation="vertical")
    ax.set_title("Medians")
    ax.grid(True, axis="x")
    for i, med in enumerate(medians_v):
        ax.annotate(str(variance_v[i]), (i, med), ha='center', va='top')


def plot_ind_vs_gen(dwoi, gens, labels, title="Hyper Volume"):
    colors = ["k", "r", "b", "c"]  # Tamir, Ami, Rand, Comb
    shapes = [".", "+", "*", "^"]  # 30, 50, 100, regular
    volume = []
    manip = []
    for i, woi in enumerate(dwoi):
        volume.append([])
        manip.append([])
        for j, d in enumerate(woi):
            volume[i].append([])
            manip[i].append([])
            fronts = []
            for w in d:
                front = np.asarray(w[:2]).T
                fronts.append(front)
            if title == "Hyper Volume":
                volume[i][j].append(round(hv.compute(fronts[-1]), 4))
            else:
                manip[i][j].append(round(np.min(fronts[-1][:, 1]), 3))
    if title == "Hyper Volume":
        ind2plot = volume
    else:
        ind2plot = manip
    plt.figure(figsize=(24.0, 10.0)).canvas.set_window_title(title)
    plt.subplots_adjust(left=0.07, bottom=0.07, right=0.98, top=0.95)
    for i, gen in enumerate(gens):
        label = labels[i]
        if "comb" in label:
            color = colors[3]
        elif "Tamir" in label:
            color = colors[1]
        elif "ami" in label:
            color = colors[0]
        elif "rand" in label:
            color = colors[2]
        if "30" in label:
            shape = shapes[3]
        elif "50" in label:
            shape = shapes[1]
        elif "100" in label:
            shape = shapes[0]
        elif "regular" in label:
            shape = shapes[2]
        ind = 0
        x = []
        y = []
        for g in gen:
            k = len(g)
            x += g
            y += ind2plot[i][ind: ind + k]
            ind += k
        x_new = []
        y_new = []
        for i in range(1240):
                med = np.median(np.asarray(y)[np.argwhere(np.asarray(x) == i)])
                if math.isnan(med):
                    continue
                y_new.append(med)
                x_new.append(i)
        plt.scatter(x_new, y_new, marker=shape, color=color, label=label)
    plt.xlabel("Generation Number", fontsize=20)
    plt.ylabel(title, fontsize=20)
    plt.grid(True)
    plt.legend()
    plt.show()


if __name__ == '__main__':
    calc_hv = False-
    create_woi_cr = False
    woi_n_generate = False
    anim = True
    plot_concept_front = False
    woi_n_generate_all = False

    fol = "/results/mutauioncheck/woi_025_075/30_runs/"
    # end_fol = ""
    sub_fols = ["mut_cr_30/", "mut_cr_50/" , "mut_cr_100/", "mut_cr_regular/"]
    names = []
    for sub in sub_fols:
        names.append([fol + sub + "ami/", fol + sub + "Tamir/", fol + sub + "rand/", fol + sub + "comb/"])
    if anim:
        for name in names:
            d = 3
            total_frames = 1240
            labels = ["ami","Tamir", "rand", "Comb"]
            woi = []
            for fold in name:
                woi.append(add_data(load_json(os.getcwd() + fold + "optimizaion_WOI")))
            fig = plt.figure()
            plt.subplots_adjust(left=0.1, bottom=0.1, right=0.98, top=0.95)
            ax = plt.axes(xlim=(-0.01, 0.5), ylim=(0, 1))
            line, = ax.plot([], [], lw=2)
            plt.grid()
            ttl = ax.text(.5, 1.02, '', transform=ax.transAxes, va='center')
            ax.set_ylabel("1 - Manipulability")
            ax.set_xlabel("Mid Proximity")
            n = 4
            lines = [plt.plot([], [])[0] for _ in range(n)]
            plot_init_woi()
            anim = animation.FuncAnimation(fig, animate_lines, init_func=init_lines,
                                   frames=total_frames/d, interval=70, repeat=False)
            Writer = animation.writers['ffmpeg']
            writer = Writer(fps=10, metadata=dict(artist='Me'), bitrate=1800)
            anim.save(os.getcwd() + fold[:-5] + 'WOI_comprasion.mp4',  writer=writer)
            plt.show()
        plt.close("all")
    if woi_n_generate:
        for name in names:
            # mutation_check(names[0], names[1], names[2])
            woi_comprasion(names=name)
    if create_woi_cr:
        names = list(itertools.chain(*names))
        for fol in tqdm(names):
            for dircetor in os.listdir(os.getcwd()+fol):
                created = False
                if os.path.isdir(os.getcwd() + fol + "/" + dircetor) and dircetor != "urdf":
                    name = fol + dircetor + "/"
                    first_gen_and_elite_res(name=name)
                    plot_cr(os.getcwd() + name + "woi_last", to_save=True)
                    plot_woi(os.getcwd() + name, to_save=True)
                    created = True
                else:
                    name = fol
                    continue
            if not created:
                print (name)
                # first_gen_and_elite_res(name=name)
                # plot_cr(os.getcwd() + name + "woi_last", to_save=True)
                # plot_woi(os.getcwd() + name, to_save=True)
    if plot_concept_front:
        fig, axs = plt.subplots(6, 1, figsize=(24, 10), facecolor='w', edgecolor='k')
        plt.subplots_adjust(left=0.05, bottom=0.07, right=0.99, top=0.99)
        colors = ["b", "k", "r", "cyan", "y", "purple"]
        points, names = all_points()
        i = 0
        major_ticks = np.arange(0, 0.5, 0.1)
        minor_ticks = np.arange(0, 0.5, 0.01)
        for conc_points, label in zip(points, names):
            x = conc_points[1]
            y = conc_points[0]
            mid_delta = 0.01
            man_delta = 0.7
            mid = x < mid_delta
            man = y < man_delta
            com = np.logical_and(mid, man)
            label = str(round(100.*np.sum(com)/np.sum(x<0.6), 1)) \
                    + "% of the result are smaller than " + str((mid_delta, man_delta))
            axs[i].scatter(x, y,  label=label, color=colors[i])
            axs[i].legend()
            axs[i].set_xticks(major_ticks)
            axs[i].set_xticks(minor_ticks, minor=True)
            axs[i].grid(which='both')
            axs[i].grid(which='minor', alpha=0.3)
            i += 1
        plt.xlabel("Mid Proximity", fontsize=26)
        axs[3].set_ylabel("1 - Manipulability", fontsize=26)
    if calc_hv:  # HV calculation
        names = list(itertools.chain(*names))
        referencePoint = [0.5, 1]
        volumes = []
        medians_v = []
        variance_v = []
        medians_l = []
        variance_l = []
        min_manip = []
        labels = []
        volumes_last =[]
        min_manip_last = []
        k = 0
        hv = HyperVolume(referencePoint)
        dwoi = []
        gens = []
        for fol in tqdm(names):
            dwoi.append([])
            gens.append([])
            last_vol = []
            last_min_manip = []
            volumes.append([])
            min_manip.append([])
            i = 0
            t = 0
            for dircetor in os.listdir(os.getcwd() + fol):
                if "hv.json" in dircetor:
                    continue
                name = fol + dircetor
                # woi_last = load_json(os.getcwd() + name + "/woi_last")["dwoi"]
                try:
                    woi_all = load_json(os.getcwd() + name + "/woi_All")
                except:
                    fix_json(os.getcwd() + name + "/woi_All", "woi_all")
                    woi_all = load_json(os.getcwd() + name + "/woi_All")
                gens[k].append([])
                for g, w in enumerate(woi_all):
                    if not dwoi[k]:
                        dwoi[k].append(w["dwoi"])
                        gens[k][t].append(g)
                        continue
                    if g < gens[k][t][-1]:
                        t += 1
                    if w["dwoi"] != dwoi[k][-1]:
                        dwoi[k].append(w["dwoi"])
                        gens[k][t].append(g)
                woi_last = woi_all[-1]["dwoi"]
                volumes[k].append([])
                min_manip[k].append([])
                for woi in woi_last:
                    front = np.asarray(woi[:2]).T
                    volumes[k][i].append(round(hv.compute(front), 4))
                    min_manip[k][i].append(np.min(front[:, 1]))
                last_vol.append(volumes[k][i][-1])
                last_min_manip.append(min_manip[k][i][-1])
                i += 1
            # save_json(os.getcwd() + fol + "last_hv", last_vol, "w+")
            volumes_last.append(last_vol)
            min_manip_last.append(last_min_manip)
            save_json(os.getcwd() + fol + "all_hv", volumes[k], "w+")
            medians_v.append(np.median(last_vol))
            variance_v.append(round(variance(last_vol), 5))
            medians_l.append(np.median(last_min_manip))
            variance_l.append(round(variance(last_min_manip), 5))
            labels.append("_".join(fol.split("/")[5:7]))
            k += 1
        plot_wilcoxon(volumes_last, medians_v, variance_v, labels)
        plot_wilcoxon(min_manip_last, medians_l, variance_l, labels, "Minimum Manipulability")
        plot_ind_vs_gen(dwoi, gens, labels, title="Hyper Volume")
        plot_ind_vs_gen(dwoi, gens, labels, title="Minimum Manipulability")

    if woi_n_generate_all:
        if not calc_hv:
            names = list(itertools.chain(*names))
        res = []
        labels = []
        for name in tqdm(names):
            all_names = []
            for fol in os.listdir(os.getcwd() + name):
                if "hv.json" in fol:
                    continue
                all_names.append(name+fol + "/")
            res.append(woi_comprasion_all(names=all_names))
            labels.append("_".join(name.split("/")[5:7]))
        colors = ["k",  "r", "b", "g", "y", "orange", "grey", "brown", "c", "purple", "m",
                  "navy", "peru", "lightgrey", "olive", "crimson", "orchid"]
        plt.ioff()
        fig, axs = plt.subplots(4, 1, figsize=(24.0, 10.0))
        plt.subplots_adjust(left=0.07, bottom=0.05, right=0.98, top=0.95)
        fig.canvas.set_window_title('30 runs WOI Comparison')
        # fig.suptitle("WOI Comparison", fontsize=26)
        j = 0
        for r, label in zip(res, labels):
            k = j / 4
            x = []
            y = []
            for i in range(len(res[0][0])):
                x.append(r[0][i])
                y.append(r[1][i])
            axs[k].plot(list(itertools.chain(*x)),list(itertools.chain(*y)), color=colors[j % 4], label=label)
            axs[k].grid(True)
            axs[k].legend(labels[k*4: k*4+4],  fontsize=10)  #, loc="upper right", bbox_to_anchor=(1, 2.5))
            j += 1
        axs[k].set_xlabel("Mid Proximity", fontsize=20)
        axs[1].set_ylabel("1 - Manipulability Index", fontsize=26)
        plt.show()
        # plt.savefig(os.getcwd() + save_folder + "/" + tit)
        # plt.close()
