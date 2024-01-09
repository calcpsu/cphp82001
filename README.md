# CalcPack HP 82001

A Li-Po battery replacement design for HP35/HP45/HP55/HP65/HP67 calculators. The original batteries had ~ 500mAh capacity, while modern Ni-MH replacements are typically ~1500mAh.

Li-Po has the advantage of far reduced self-discharge in comparison to Ni-MH, which is an advantage for an intermittently-used device. Even with similar mAh capacity, we can expect longer battery life.

Ni-MH / Ni-CD batteries are notorious for leaking. While Lithium Ion batteries are notorious for self-immolation, a well protected Li-Po battery (particularly in a low current application like this) should be able to be made very safe.

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
     - Very low Iq for a regulator (25uA)
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

Addition of a series regulator is not an immediately obvious means to maximise efficiency. I've observed the HP-35 increases current consumption as voltage rises (this is most likely a result of the way the LEDs are driven with fixed-duty inductive energy, this appears as brighter leds!). Even accounting for the linear loss and Iq of the regulator circuit, total power consumption decreases as the regulator voltage decreases (down to about 3.6V, the minimum to operate the calculator reliably).

A model of the discharge shows 3.6V to be the optimum for run time, including the impact of the dropout voltage on termination for Vbat.

Essential for this is the very low dropout of the regulator chosen - if this increases to more than about 150mV, then the performanace advantage is lost!

For the HP65/67, the card reader benefits from a consistent voltage applied. Ensuring this is high enough for a reliable card read and write (and allowing for a little droop during this process) means I'm picking 3.7~3.8V as a regulation voltage.

![Graph of discharge performance model]()

### Why not a switching regulator?

In theory, replacing the series linear regulator with a switching regulator may allow use of the battery capacity right down to 3.0V, and more efficiently use the currently wasted energy of the full battery (VB+ > 3.7V) currently being dissipated by the linear reg.

Unfortunately, as the VB+ is close to Vout required, a topology able to deal with VB+ both above and below Vout is needed. The target efficiency to outperform the linear regulator would be 93.8%. Typical switching regulator arrangements are unlikely to do much better than 80% at this current level, with vastly higher Iq also (reducing the power-off battery time).
