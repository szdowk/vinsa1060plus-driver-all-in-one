# 10moons-driver-vin1060plus

Forked from Alex-S-V ( thanks dude for the pyUSB intro ) 

![Aliexpress Graphics Tablet VINSA 1060plus](http://eng.10moons.com/upload/2018/06/11/201806112311552.jpg)

[10moons Graphics Tablet product homepage](http://eng.10moons.com/info5494.html)

[Aliexpress equivalent sold under VINSA brand. --- Download User Manual](http://blog.ping-it.cn/h/8/sms.pdf)

This is a Simple driver with pyUSB code modified to handle the interaction events of the VINSA 1060Plus graphics tablet, that includes a passive two button pen.

Linux detects it as a T501 GoTOP tablet,  hence pyUSB library is able to interface with the tablet device.

## About

Driver which provides basic functionality for VINSA 1060plus T501 tablet:
* 12 buttons on the tablet itself
* Correct X and Y positioning (two active area modes present:  Android Active Area & Full Tablet Active Area)
* Pressure sensitivity ( able to read the values, but unable to pass it onto Graphics Software )

Tablet has 4096 levels in both axes and 2047 levels of pressure ( Product description says 8092, but actual output readings are 2047 max).

## The progress so far...

With linux Kernel 5+,  the graphics tablet should be detected but pen movement is restricted to Android Active Area (the small area on the tablet).  That driver was added to the kernel but interacts with the T503 chipset. 
Thanks to [Digimend - https://github.com/DIGImend](https://github.com/DIGImend) for providing valuable functionality not just to 10moons Tablets, but to a variety of other popular Tablets.

Unfortuantely, Mr Digimend has chosen not to further develop the driver applicable to VINSA 1060plus, due to the inaccurate information transmitted between the T501 chipset and the USB driver --> [Live recording of Mr DIGIMEND working on 10moons tablet debug and analysis.  Awesome to see the master at work :)](https://www.youtube.com/watch?v=WmnSwjlpRBE).

So an alternative workaround was needed.  In steps Alex-S-V with his pyUSB implementation of the T503 driver --- together with the [Digimend 10moons-Probe tool](https://github.com/DIGImend/10moons-tools),  it has the particular effect of switching the Graphics Tablet out of AndroidActiveArea Mode and into FullTabletArea mode.  I will need to ask the original author (Mr.Digimend) how he identified the hex string to transmit to the tablet (probe.c src: line#165 ---> SET_REPORT(0x0308, 0x08, 0x04, 0x1d, 0x01, 0xff, 0xff, 0x06, 0x2e); )[https://github.com/DIGImend/10moons-tools/blob/6cc7c40c50cb58fefe4e732f6a94fac75c9e4859/10moons-probe.c#L165]

The person to discover this "hack" was Mr.Digimend himself and thanks to the [Youtube video that he uploaded time-stamp @1:40.11](https://youtu.be/WmnSwjlpRBE?t=6011) he shows that usbhid-dump  output when in Android-Active-Area Mode (8 byte TX)  vs  the required  Full-Tablet-Active-Area mode ( 64 byte TX).


## How to install
1. Clone or Dowload then install  [`10moons-tools`](https://github.com/DIGImend/10moons-tools)
2. run  `lsusb` ... identify  BUS and DEVICE numbers that linux detects from Graphics Tablet
    e.g. Bus 001 Device 003: ID 08f2:6811 Gotop Information Inc. [T501] Driver Inside Tablet
3. run  `sudo 10moons-tools BUSnum DEVICEnumber`
    e.g. sudo 10moons-tools 1 3
4. Clone or download then install this repository.
    4.1. 
        git clone https://github.com/f-caro/10moons-driver-vin1060plus.git
    4.2. Then install all dependencies listed in `_requirements.txt_` file either using python virtual environments or not.
        python3 -m pip install -r requirements.txt

5. run python driver ---  `sudo python3 driver-vin1060plus.py`

6. remember to tap the graphics tablet with the passive pen, so that the linux xinput can list it as a virtual pointing device (a quirk maybe associated with vin1060plus ?!)

7.  In case of multiple monitors connected.
    7.1. run `xrandr` --->  to identify the name of the Display that you want to limit your tablet x & y coords.
        e.g.  DisplayPort-1
    7.2. run `xinput`  ---> to list all virtual devices,  identify the virtual core pointer associated with tablet pen
        e.g.   ↳ 10moons-pen Pen (0)                     	id=17	[slave  pointer  (2)]
    7.3. configure xinput to restrict x&y coords to relevant monitor
        e.g.  xinput map-to-output 17 DisplayPort-1


**You need to connect your tablet and run the driver prior to launching a drawing software otherwise the device will not be recognized by it.**





## Configuring tablet

Configuration of the driver placed in _config.yaml_ file.

You may need to change the *vendor_id* and the *product_id* but I'm not sure (You device can have the same values as mine, but if it is not you can run the *lsusb* command to find yours).

Buttons assigned from in the order from left to right. You can assign to them any button on the keyboard and their combinations separating them with a plus (+) sign.

If you find that using this driver with your tablet results in reverse axis or directions (or both), you can modify parameters *swap_axis*, *swap_direction_x*, and *swap_direction_y* by changing false to true and another way around.

To list all the possible key codes you may run:
```
python -c "from evdev import ecodes; print([x for x in dir(ecodes) if 'KEY' in x])"
```

## Credits

Some parts of code are taken from: https://github.com/Mantaseus/Huion_Kamvas_Linux
Other parts taken from:  

## Known issues

Buttons on the pen itself do not work and hence not specified. I don't know if it's the issue only on my device or it's a common problem.
