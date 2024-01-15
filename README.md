# CalcPack HP 82001

A Li-Po battery replacement design for HP35/HP45/HP55/HP65/HP67 calculators. The original batteries had ~ 500mAh capacity, while modern Ni-MH replacements are typically ~1500mAh.

Li-Po has the advantage of far reduced self-discharge in comparison to Ni-MH, which is an advantage for an intermittently-used device. Even with similar mAh capacity, we can expect longer battery life.

Ni-MH / Ni-CD batteries are notorious for leaking. While Lithium Ion batteries are notorious for self-immolation, a well protected Li-Po battery (particularly in a low current application like this) should be able to be made very safe.

![Render of calcpack PCB](https://github.com/calcpsu/cphp82001/blob/master/docs/cphp82001-pcb_render.png?raw=true)

## Features / design goals:
- Fit into existing compartment with no modifications
- Similar or ideally exceed capacity of standard Ni-Cd or Ni-MH 3xAA types (1200~2200mAh)
- Dual charge - USB (externally) or in-place using original HP charger
- Battery charge control and protection
- Maximise battery life:
    - Minimise Iq to maximise time between charges (shelf time)
    - Minimise voltage drop / series resistance of circuits to maximise run time
    - Optimise Vout to minimise calculator power consumption

## References 
This has been inspired by the below reference projects:
 - https://www.edn.com/classic-hp-35-calculator-comes-back-to-life/
   - GOOD: Regulated (see reasoning in the article, and discussion below)
   - BAD: Has no charging circuit / must remove to charge
   - BAD: Cannot connect HP charger (would cause dangerous overcharge condition; best case trip battery OC protection)
 - https://hackaday.io/project/175815-classic-hp-calculator-lipo-battery-pack
   - GOOD: Has on-board charge controller
   - BAD: Has no regulation
   - GOOD: Can connect HP charger, but
   - BAD: Unable to charge from HP charger / must remove to charge

## Key Components
 - Battery:
     - 10x34x50mm lipo pouch cell. These also include a DW01A/FS8205 protection circuit.
 - Charge controller: [BQ21040](https://www.ti.com/lit/ds/symlink/bq21040.pdf)
     - Wide voltage input range (over voltage protected)
     - Clever voltage foldback mode (which will help with constant current supply charging)
     - Variable current setting
     - Safety timer (10h) and 10% termination current
 - Regulator: [TLV75801](https://www.ti.com/lit/ds/symlink/tlv758p.pdf)
     - Ultra low dropout (~30mV)
     - 500mA current (enough for HP67 card read/write at ~400mA for a few seconds)
     - Very low Iq for a regulator (25uA at idle, assuming Vb > Vo; only 400uA or so at full current)
 - Output protection diode: [MAX40203](https://www.analog.com/media/en/technical-documentation/data-sheets/MAX40203.pdf)
     - Low voltage drop (~40mV) ideal diode
     - Low leakage and low Iq (<0.5uA)
 - Undervoltage protection: [TPS3808](https://www.ti.com/lit/ds/symlink/tps3808.pdf)
     - Set level with a voltage divider - e.g. ~3.0V for better battery health
     - Output used to shutdown regulator and output diode, disconnecting load and vastly reducing Iq
     - Actual protective disconnection of battery done at ~2.5V by battery pack protection circuit (typically DW01A/FS8205)
 - Input overvoltage protection: [NCP360SNT]()
     - Cuts off USB input for overvoltage condition (note that 2x rated voltage is required by compliance test standard EN38.3 T.7, required for transport of lipo batteries in USA/EU).

## Function Description
![Block diagram of battery](https://github.com/calcpsu/cphp82001/blob/master/docs/blockdiagram.png?raw=true)
### Discharging, calculator on:
 - Charge controller is powered down (VCC < VBAT)
 - B+ supplies regulator, which regulates to 3.70V
 - Output delivered to calculator via ideal diode
 - Up to 16h run time estimated
### Charging, USB:
 - VBUS at Q1 G pulls prog down to 5k (250mA)
 - VBUS supplies VCC via D1
 - Charge controller charges battery at full 0.2C current
 - Physically not possible to do inside the calculator, can assume HP input disconnected
### Charging, HP charger:
 - VCC supplied via D5, from HP 50mA CC sppply. Voltage limited by D2 (although BQ21040 will tolerate up to 30V, want it to stay below 6.6V to prevent OVP activation).
 - Q1 off. Charge controller prog resistor charges at ~45mA
 - Ideal diode reverse biased (off).
 - HP35/45/55 calculators do not draw current when on - supplied separately by HP AC adapter.
 - HP65/67 with card reader: card reader may draw from battery supply. In this case, the CC supply voltage will drop until ideal diode is activated, and card reader is powered from regulator (3.7V). This will result in VCC < Vbat for a while, resetting the charge controller and beginning a new recharge cycle. As the AC adapter is not sufficient to run the card reader, this is the least worst outcome available.
### Battery Exhausted:
 - HP35 shows low battery (decimal points) indication at V+ of 3.50V
   - This represents about 6-7% charge state of LiPo
   - User may switch off and recharge now...
 - HP35 will cease to function at ~3.25V, still draws ~75mA
   - User probably should switch off and recharge now...
 - U4 protects battery at VB+ = ~3.0V, by disabling the regulator and output diode. Iq should be ~10uA.
   - Plenty of time to recharge at this voltage, which is good for battery health.
 - If left for a long time, VB+ may reduce to 2.5V, which should trigger battery pack protection circuit and fully disconnect the battery. Plugging in (turning on charge controller, which will do a battery detection routine and reset the protection circuit) will reset.

## Notes on optimisation:

Addition of a series regulator is not an immediately obvious means to maximise efficiency. I've measured the HP-35 increases current consumption as voltage rises (this is most likely a result of the way the LEDs are driven with fixed-duty inductive energy, this appears as brighter leds). Even accounting for the linear loss and Iq of the regulator circuit, total power consumption decreases as the regulator voltage decreases (down to about 3.6V, the minimum to operate the calculator reliably). The newer models (HP-45, HP-67) do the opposite - the current drops as the voltage increases, I believe there must be some kind of improved more efficient power supply arrangement. The HP-67 has a card reader with a motor; this draws around 400mA when reading/writing a card; it is necessary to ensure a sufficient buffer above the minimum/low battery voltage to ensure read/write operations work well, and ensuring a stiff power supply is beneficial for consistent operation.

### Why not a switching regulator?

In theory, replacing the series linear regulator with a switching regulator may allow use of the battery capacity right down to 3.0V, and more efficiently use the currently wasted energy of the full battery (VB+ > 3.63V) currently being dissipated by the linear reg.

I've investigated using a MIC2250 step-up regulator, which has a surprisingly low Iq (55uA, not switching), and could provide a consistent output voltage right down to the end of the battery capacity (Vb=3.0V). At the currents needed, this can be around 87% efficient. This would provide a consistent voltage right up until shutdown. While this might be good particularly for the HP-67 card reader, it has the disadvantage of skipping the calculator's built-in low battery indication - the power supply unit would completely shutdown without any warning with a low battery.

### Model of 3 options

I've done a simulation of the 3 options:

  1. No regulator (default - calculator supplied with battery voltage via MAX40203 diode)
  2. Linear regulator (TLV75801, set to 3.80V)
  3. Switchmode step-up regulator (MIC2250, set to 3.80V also)

For each, the model calculates the change in output voltages given the battery state, calculator and power supply current draw, and iterates until the 2000mAh battery is exhausted. The calculator load is measured from 3 sample calculators, reflecting the calculator being left on in the default display ("0." or "0.00" depending on the model), and accounts for the changing current with changing supply voltage. Results are shown below.

In summary, a regulated design gains a slight advantage in run time for the HP-35, while slightly reducing run time for HP-45 and HP-67. The switchmode design is best for the current-hungry HP-67, but not by a significant amount.
Given the linear regulator provides some additional advantages for all the calculators (including a level of overcurrent / short-circuit protection which would need to be replaced, the function of the calculator's low battery signal is retained, and a more consistent voltage for the HP-67 including reducing voltage droop during card reads), the penalty in run time (and shelf time) I think is justified and the linear regulator is the optimum solution.

#### Results summary (t in hours)
![Image of power model results](https://github.com/calcpsu/cphp82001/blob/master/powermodel/modelresults.png?raw=true)
#### HP-35
![Image of power model results](https://github.com/calcpsu/cphp82001/blob/master/powermodel/results_hp35.png?raw=true)
#### HP-45
![Image of power model results](https://github.com/calcpsu/cphp82001/blob/master/powermodel/results_hp45.png?raw=true)
#### HP-67
![Image of power model results](https://github.com/calcpsu/cphp82001/blob/master/powermodel/results_hp67.png?raw=true)


## License

This work is licensed under a
[Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License][cc-by-nc-sa].

[![CC BY-NC-SA 4.0][cc-by-nc-sa-image]][cc-by-nc-sa]

[cc-by-nc-sa]: http://creativecommons.org/licenses/by-nc-sa/4.0/
[cc-by-nc-sa-image]: https://licensebuttons.net/l/by-nc-sa/4.0/88x31.png
[cc-by-nc-sa-shield]: https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg
