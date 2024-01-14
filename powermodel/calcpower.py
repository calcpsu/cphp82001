import pandas as pd
from scipy.interpolate import CubicSpline, interp1d
import matplotlib.pyplot as plt
import numpy as np

# battery properties
mah = 2000 #mAh
capacity_start = 100 # %

# calculator properties
calculators = [{"name":"hp35","v_stop":3.5},{"name":"hp45","v_stop":3.5},{"name":"hp67","v_stop":3.6}]

# linear reg properties
reg_vset = 3.80 #V
reg_vdo = 0.030 #V
reg_iq = 0.030 #mA (not including actual regulator; ignd is separate)
reg_iq_shutdown = 0.019 #mA

# noreg properties
noreg_iq = 0.0245 #mA
noreg_iq_shutdown = 0.019 #mA

# switchmode reg properties
sm_vset = reg_vset #V
sm_vdiode = 0.40 #V
sm_iq = 0.090 #mA
sm_iq_shutdown = 0.019 #mA

# commong properties
max20300_vd = 0.030 #V
v_cutout = 3.10 #V

results = []

if __name__ == "__main__":

  print("CALCPSU MODELLER")

  for calc in calculators:

    # derive load function
    df_load = pd.read_csv("load_"+calc["name"]+".csv")
    #print(df_load)
    loadfunc = CubicSpline(df_load["voltage"], df_load["current"], extrapolate=False)
    #plotrange = np.linspace(start=3.0,stop=4.2,num=100)
    #plt.plot(plotrange, loadfunc(plotrange))
    #plt.show()

    # derive battery function
    df_batt = pd.read_csv("battery.csv")
    battfunc = CubicSpline(df_batt["capacity"], df_batt["voltage"], extrapolate=False)
    #plotrange = np.linspace(start=0, stop=100,num=101)
    #plt.plot(plotrange, battfunc(plotrange))
    #plt.show()

    # derive sm converter efficiency function
    df_eff = pd.read_csv("efficiency_mic2250.csv")
    efffunc = CubicSpline(df_eff["current"], df_eff["efficiency"], extrapolate=False)
    #plotrange = np.logspace(start=-1, stop=3,num=101)
    #plt.xscale("log")
    #plt.plot(plotrange, efffunc(plotrange),)
    #plt.show()

    df_regignd = pd.read_csv("ignd_tlv75801.csv")
    reg_ignd_func = interp1d(df_regignd["current_out"], df_regignd["current_gnd"])

    df_regvdo = pd.read_csv("vdo_tlv75801.csv")
    reg_vdo_func = interp1d(df_regvdo["current"], df_regvdo["voltage"])

    t_max = 24.0 #hours
    numsteps = int(t_max)*60 + 1

    trange = np.linspace(start=0,stop=t_max,num=numsteps)
    tstep = trange[1]-trange[0]
    capacity_noreg = capacity_start/100 * mah
    capacity_reg = capacity_start/100 * mah
    capacity_sm = capacity_start/100 * mah

    datalist_noreg = []
    datalist_reg = []
    datalist_sm = []

    for t in trange:
      # no regulator
      d = {}
      d["t"] = t
      d["c"] = capacity_noreg
      d["vb"] = battfunc(capacity_noreg/mah*100) # V
      if d["vb"] < v_cutout:
        d["vo"] = 0.0
        d["io"] = noreg_iq_shutdown
        d["ib"] = noreg_iq_shutdown
      else:
        d["vo"] = d["vb"] - max20300_vd #V
        d["io"] = loadfunc(d["vo"]) #mA
        d['ib'] = d['io'] + noreg_iq #mA
      d["cu"] = d["ib"] * tstep #mAh
      if capacity_noreg < 0.0:
        capacity_noreg = 0.0
      capacity_noreg = capacity_noreg - d["cu"]
      datalist_noreg.append(d.copy())

      # regulator 
      d = {}
      d["t"] = t
      d["c"] = capacity_reg
      d["vb"] = battfunc(capacity_reg/mah*100) # V
      if d["vb"] < v_cutout:
        d["vo"] = 0.0
        d["io"] = 0.0
        d["ib"] = reg_iq_shutdown
      else:
        vo_estimate = min(reg_vset, d["vb"]) - max20300_vd #V, first estimate (no vdo yet)
        io_estimate = loadfunc(vo_estimate) #mA, first estimate
        vdo_estimate = reg_vdo_func(io_estimate)
        if d["vb"] > vo_estimate + vdo_estimate:
          # regulation
          d["vo"] = reg_vset - max20300_vd #mA
        else:
          # dropout
          d["vo"] = d["vb"] - vdo_estimate
        d["io"] = loadfunc(d["vo"]) #mA
        d["ib"] = d["io"] + reg_ignd_func(d["io"]) + reg_iq #mA
      d["cu"] = d["ib"] * tstep #mAh
      capacity_reg = capacity_reg - d["cu"]
      if capacity_reg < 0.0:
        capacity_reg = 0.0
      datalist_reg.append(d.copy())
      #print(d)

      # switchmode
      d = {}
      d["t"] = t
      d["c"] = capacity_sm
      d["vb"] = battfunc(capacity_sm/mah*100) # V
      if d["vb"] > sm_vset + sm_vdiode:
        d["vo"] = d["vb"] - sm_vdiode - max20300_vd #V
        d["io"] = loadfunc(d["vo"]) #mA
        d["ib"] = d["io"] + sm_iq #mA (straight through)
      elif d["vb"] < v_cutout:
        d["vo"] = 0.0
        d["io"] = 0.0
        d["ib"] = sm_iq_shutdown
      else:
        d["vo"] = sm_vset - max20300_vd #V
        d["io"] = loadfunc(d["vo"])
        e = efffunc(d["io"])/100 #mW/mW
        d["ib"] = ((d["io"] * sm_vset) / e / d["vb"]) + sm_iq #
      d["cu"] = d["ib"] * tstep #mAh
      capacity_sm = capacity_sm - d["cu"]
      if capacity_sm < 0.0:
        capacity_sm = 0.0
      datalist_sm.append(d.copy())
      #print(d)

    df_noreg = pd.DataFrame(datalist_noreg)
    df_noreg.set_index("t", inplace=True)
    df_reg = pd.DataFrame(datalist_reg)
    df_reg.set_index("t", inplace=True)
    df_sm = pd.DataFrame(datalist_sm)
    df_sm.set_index("t", inplace=True)

    t_stop_noreg = df_noreg[df_noreg["vo"]<calc["v_stop"]].index[0]
    t_stop_reg = df_reg[df_reg["vo"]<calc["v_stop"]].index[0]
    t_stop_sm = df_sm[df_sm["vo"]<calc["v_stop"]].index[0]

    fig, axs = plt.subplots(3,1, constrained_layout=True)
    fig.set_size_inches(10,10)

    # ax0
    axs[0].set_title(calc["name"] + " Capacity")
    axs[0].set_ylabel("mAh")
    
    axs[0].plot(df_noreg.index, df_noreg["c"], 'r-', label='no reg')
    axs[0].plot(df_reg.index, df_reg["c"], 'g-', label='reg')
    axs[0].plot(df_sm.index, df_sm["c"], 'b-', label='sm')

    #ax 1
    axs[1].set_title(calc["name"] + " Current")
    axs[1].set_ylabel("mA")

    axs[1].plot(df_noreg.index, df_noreg["io"], 'r-', label="io, no reg")
    axs[1].plot(df_reg.index, df_reg["io"], 'g-', label="io, reg")
    axs[1].plot(df_sm.index, df_sm["io"], 'b-', label="io, sm")
    axs[1].plot(df_noreg.index, df_noreg["ib"], 'r:', label="ib, no reg")
    axs[1].plot(df_reg.index, df_reg["ib"], 'g:', label="ib, reg")
    axs[1].plot(df_sm.index, df_sm["ib"], 'b:', label="ib, sm")

    # ax 2
    axs[2].set_title(calc["name"] + " Voltage")
    axs[2].set_ylabel("V")

    axs[2].plot(df_noreg.index, df_noreg["vo"], 'r-', label='vo, noreg')
    axs[2].plot(df_reg.index, df_reg["vo"], 'g-', label='vo, reg')
    axs[2].plot(df_sm.index, df_sm["vo"], 'b-', label='vo, sm')
    axs[2].plot(df_noreg.index, df_noreg["vb"], 'r:', label='vb, noreg')
    axs[2].plot(df_reg.index, df_reg["vb"], 'g:', label='vb, reg')
    axs[2].plot(df_sm.index, df_sm["vb"], 'b:', label='vb, sm')
    
    ylim = axs[2].get_ylim()
    axs[2].axline([t_stop_noreg,ylim[0]],[t_stop_noreg,ylim[1]], color='red', linestyle="--")
    axs[2].text(x=t_stop_noreg, y=ylim[0], s="t={0:.1f}".format(t_stop_noreg), ha='right', va='bottom', rotation='vertical', color="red")
    axs[2].axline([t_stop_reg,ylim[0]],[t_stop_reg,ylim[1]], color='green', linestyle="--")
    axs[2].text(x=t_stop_reg, y=ylim[0], s="t={0:.1f}".format(t_stop_reg), ha='right', va='bottom', rotation='vertical', color="green")
    axs[2].axline([t_stop_sm,ylim[0]],[t_stop_sm,ylim[1]], color='blue', linestyle="--")
    axs[2].text(x=t_stop_sm, y=ylim[0], s="t={0:.1f}".format(t_stop_sm), ha='right', va='bottom', rotation='vertical', color="blue")
    
    axs[2].legend()

    # common formatting
    for ax in axs:
      ax.set_xlabel("hours")
      ax.set_xticks(range(0,25,2))
      ax.set_xlim([0,24])
      ax.grid(axis='x')
      ax.legend()

    #plt.show()
    plt.savefig("results_" + calc["name"] + ".png")
    results.append({"calc":calc["name"], "t_noreg":t_stop_noreg, "t_reg":t_stop_reg, "t_sm":t_stop_sm})

  df_results = pd.DataFrame(results).set_index("calc")

  print("vreg={0}".format(sm_vset))
  print(df_results)