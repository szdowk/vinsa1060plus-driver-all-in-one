# ##########################################################################################################
# Driver for tablette VINSA 1060 plus based on «f-caro» (https://github.com/f-caro), and inspired by
# Alexandr Vasilyev - «alex-s-v» (https://github.com/alex-s-v)
#
# I've put everything inside this script (reclaim interface) - open full area - source of Alexandr and
# I 've added the management of buttons on top of the tablet. 
# 21/09/2024 - Delfosse Aurore (ON7AUR) - V0.1 - first release
# 30/06/2025 - Debugging of pen buttons support and some optimalizations (key map) by szdowk
# 18/10/2025 - Debugging of "Resource busy" error, sleep/hibernate support and usb errors handle by szdowk
#
# ##########################################################################################################

import os
import sys
import shutil
import time
# Specification of the device https://python-evdev.readthedocs.io/en/latest/
from evdev import UInput, ecodes, AbsInfo
# Establish usb communication with device
import usb
import usb.core
import usb.util
# Read configuration
import yaml

# ##########################################################################################################
# Global variables
# ##########################################################################################################
DEBUG = False	# Default mode, try "--debug" line option for debug mode.

# ##########################################################################################################
# Options
# ##########################################################################################################
for arg in sys.argv[1:]:
    if arg == "--debug": DEBUG = True

# ##########################################################################################################
# Functions
# ##########################################################################################################
def probe(bus_num, dev_addr):
    # Initialisation du contexte USB
    dev = usb.core.find(bus=bus_num, address=dev_addr)
    
    if dev is None:
        print("Device not found")
        return 1

    # Exemple de transmission de rapports
    def set_report(wValue, report):
        try:
            dev.ctrl_transfer(0x21, 9, wValue, 2, report, 250)
        except usb.core.USBError as e:
            print(f"Error setting report: {e}")
            return 1
        return 0

    reports = [
        (0x0308, [0x08, 0x04, 0x1d, 0x01, 0xff, 0xff, 0x06, 0x2e]),
        (0x0308, [0x08, 0x03, 0x00, 0xff, 0xf0, 0x00, 0xff, 0xf0]),
        (0x0308, [0x08, 0x06, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00]),
        (0x0308, [0x08, 0x03, 0x00, 0xff, 0xf0, 0x00, 0xff, 0xf0]),
    ]
    
    for i, (wValue, report) in enumerate(reports):
        result = set_report(wValue, report)
        if result != 0:
            print(f"Failed at report {i}")
            return result

    # Libération de l'interface
    usb.util.release_interface(dev, 2)
    return 0

def run_probe_on_iface2(dev):
    """Zakłada, że iface 2 jest już zclaimowany; wysyła sekwencję raportów 'full area'."""
    def set_report(wValue, report):
        dev.ctrl_transfer(0x21, 9, wValue, 2, report, 250)
        time.sleep(0.01)
    set_report(0x0308, [0x08, 0x04, 0x1d, 0x01, 0xff, 0xff, 0x06, 0x2e])
    set_report(0x0308, [0x08, 0x03, 0x00, 0xff, 0xf0, 0x00, 0xff, 0xf0])
    set_report(0x0308, [0x08, 0x06, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00])
    set_report(0x0308, [0x08, 0x03, 0x00, 0xff, 0xf0, 0x00, 0xff, 0xf0])

def setup_device_for_full_area(dev):
    # 0) Try to unload kernel drivers (nothing will happen if already unloaded)
    for i in (0, 1, 2):
        try:
            if dev.is_kernel_driver_active(i):
                dev.detach_kernel_driver(i)
        except Exception:
            pass

    # Reset
    try:
        dev.reset()
    except usb.core.USBError:
        # after resume some controlers do reset – lets ignore
        pass

    # set_configuration with  retry i EBUSY (16) support
    for _ in range(3):
        try:
            dev.set_configuration()
            break
        except usb.core.USBError as e:
            err = getattr(e, "errno", None) or (e.args[0] if e.args else None)
            if err == 16:  # Resource busy
                # Lets try again and additional detach
                for i in (0, 1, 2):
                    try:
                        if dev.is_kernel_driver_active(i):
                            dev.detach_kernel_driver(i)
                    except Exception:
                        pass
                time.sleep(0.05)
                continue
            else:
                raise

    # full-area: claim iface 2, reports, release 2
    usb.util.claim_interface(dev, 2)
    run_probe_on_iface2(dev)
    usb.util.release_interface(dev, 2)

    # read from iface 1
    usb.util.claim_interface(dev, 1)
    ep = dev[0].interfaces()[1].endpoints()[0]
    return ep


# ##########################################################################################################
# Main #####################################################################################################
# ##########################################################################################################
if __name__ == "__main__":
    # Check existing directory ~/.config/driver-vin1060plus - if not create it and Copy inside the yaml
    #if not os.path.exists(os.path.join(os.path.expanduser(".config/driver-vin1060plus"), "config-vin1060plus.yaml" )):
    if not os.path.exists(os.path.join(os.path.expanduser('~'), ".config/config-vin1060plus/config-vin1060plus.yaml" )):
        print("yaml not found")
        # creat directory
        print(f"create directory : {os.path.join(os.path.expanduser('~'), '.config/config-vin1060plus')}")
        os.makedirs(os.path.join(os.path.expanduser('~'), ".config/config-vin1060plus"))
        # copy file 
        shutil.copy("./config-vin1060plus.yaml", os.path.join(os.path.expanduser('~'), ".config/config-vin1060plus/config-vin1060plus.yaml" ))

    # Open yaml file from :
    path = os.path.join(os.path.expanduser('~'), ".config/config-vin1060plus/config-vin1060plus.yaml")
    # if we compile the solution with Nuitka - user should be able to map his own keys via this file

    # Loading tablet configuration
    with open(path, "r") as f:
        config = yaml.load(f, Loader=yaml.FullLoader)

    # tabus=$(lsusb|grep 08f2:6811|gawk '{print $2;print $4}'|tr '\n' ' '|tr ':' ' ')
    # -> adress is in the yaml
    tabus=usb.core.find(idVendor=config["vendor_id"], idProduct=config["product_id"])
    if tabus==None :
        print("Vinsa 1060Plus not found - check if vendor:product correspond from «lsusb» and in the config File")
        print(f"Your config file is :{os.path.join(os.path.expanduser('~'), '.config/config-vin1060plus/config-vin1060plus.yaml')}")
        exit(-1)

    probe(tabus.bus, tabus.address)
    # HERE : Full area open
    # ######################################################################################################

    # Get the required ecodes from configuration
    pen_codes = []
    btn_codes = []
    for k, v in config["actions"].items():
        codes = btn_codes if k == "tablet_buttons" else pen_codes
        if isinstance(v, list):
            codes.extend(v)
        else:
            codes.append(v)

    if(DEBUG) : print("codes", codes)
    if(DEBUG) : print("pen_codes", pen_codes)
    if(DEBUG) : print("btn_codes", btn_codes)

    temp = []
    for c in pen_codes:
        temp.extend([ecodes.ecodes[x] for x in c.split("+")])
    pen_codes = temp

    temp = []
    for c in btn_codes:
        temp.extend([ecodes.ecodes[x] for x in c.split("+")])
    btn_codes = temp

    pen_events = {
        ecodes.EV_KEY: pen_codes,
        ecodes.EV_ABS: [
            #AbsInfo input: value, min, max, fuzz, flat
            (ecodes.ABS_X, AbsInfo(0, 0, config["pen"]["max_x"], 0, 0, config["pen"]["resolution_x"])),         
            (ecodes.ABS_Y, AbsInfo(0, 0, config["pen"]["max_y"], 0, 0, config["pen"]["resolution_y"])),
            #dont calculate absolute x-max/x-min or y-max/y-min values when multiple displays used
            #rather use xrandr and xinput together to configure which display handles the virtual pen ID
            #eg. xinput map-to-output 17 DisplayPort-1
            (ecodes.ABS_PRESSURE, AbsInfo(0, 0, config["pen"]["max_pressure"], 0, 0, 1))
        ],
    }

    btn_events = {ecodes.EV_KEY: btn_codes}
    if(DEBUG) : print("pen_events :: ", pen_events)
    if(DEBUG) : print("btn_events :: ", btn_events)

    # Find the device
    dev = usb.core.find(idVendor=config["vendor_id"], idProduct=config["product_id"])
    # Select end point for reading second interface [2] for actual data
    # Interface[0] associated Internal USB storage (labelled as CDROM drive)
    # Interface[1] useful to map 'Full Tablet Active Area' -- outputs 64 bytes of xinput events
    # Interface[2] maps to the 'AndroidActive Area' --- outputs 8 bytes of xinput events ( but only before  ./10moons-probe is executed)
    if(DEBUG) : print(dev)
    if(DEBUG) : print("--------------------------------")
    if(DEBUG) : print("---Drop default kernel driver from all devices")

    if(DEBUG): print("--- setup_device_for_full_area(dev)")
    ep = setup_device_for_full_area(dev)

    vpen = UInput(events=pen_events, name=config["xinput_name"], version=0x3)
    if(DEBUG) : print(vpen.capabilities(verbose=True).keys() )
    if(DEBUG) : print(vpen.capabilities(verbose=True) )
    vbtn = UInput(events=btn_events, name=config["xinput_name"] + "_buttons", version=0x3)  

    #compare with xinput list
    if(DEBUG) : print(vbtn.capabilities(verbose=True).keys() )
    if(DEBUG) : print(vbtn.capabilities(verbose=True) )
    if(DEBUG) : print(vpen)
    if(DEBUG) : print(vbtn)

    pressed = -1

    # Direction and axis configuration
    max_x = config["pen"]["max_x"] * config["settings"]["swap_direction_x"]
    max_y = config["pen"]["max_y"] * config["settings"]["swap_direction_y"]
    if config["settings"]["swap_axis"]:
        y1, y2, x1, x2 = (1, 2, 3, 4) 
    else:
        x1, x2, y1, y2 = (1, 2, 3, 4)
        
    #Pen pressure thresholds:
    pressure_max = config["pen"]["max_pressure"]
    pressure_min = config["pen"]["pressure_min"]
    pressure_contact_threshold = config["pen"]["pressure_contact_threshold"]
    #Unfortunately vin1060plus does not show 8192 pressure resolution.  #TODO: need to review pressure parameters

    pressed_prev = None
    pen_pressed_prev = None

    button_map = {
        (255, 49):  0,   # key E
        (255, 35):  1,   # key B
        (127, 51):  2,   # CTRL-
        (255, 50):  3,   # CTRL+
        (191, 51):  4,   # [
        (255, 19):  5,   # ]
        (223, 51):  6,   # scroll up
        (254, 51):  7,   # TAB
        (239, 51):  8,   # scroll down
        (253, 51):  9,   # SPACE
        (247, 51): 10,   # CTRL
        (251, 51): 11,   # ALT
    }

    # ######################################################################################################
    # Infinite loop
    # ######################################################################################################

    short_streak = 0
    idle_timeouts = 0

    while True:
        try:
            # 1) Read with timeout (1 s)
            try:
                data = dev.read(ep.bEndpointAddress, ep.wMaxPacketSize, timeout=1000)
                idle_timeouts = 0  # if recaived data
            except usb.core.USBTimeoutError:
                # In some situations except USBTimeoutError there is USBError 110;
                # it will be cached below, so there just re-raise:
                raise
            except usb.core.USBError as e:
                # If time passed, the tablet is inactive
                err = getattr(e, "errno", None)
                if err is None and e.args:
                    err = e.args[0]
                if err == 110:  # Operation timed out
                    idle_timeouts += 1
                    delay = min(0.05, 0.001 * idle_timeouts)  # 50ms max
                    if DEBUG and idle_timeouts % 60 == 0:
                        print(f"[USB] idle timeout x{idle_timeouts} (delay={delay:.3f}s)")
                    time.sleep(delay)
                    # Lets „refresh” interface after long silence:
                    if idle_timeouts >= 600:  # ~10 minutes of silence
                        if DEBUG: print("[USB] long idle – soft re-claim iface 1")
                        try: usb.util.release_interface(dev, 1)
                        except Exception: pass
                        try: usb.util.claim_interface(dev, 1)
                        except usb.core.USBError: pass
                        ep = dev[0].interfaces()[1].endpoints()[0]
                        idle_timeouts = 0
                    continue
                else:
                    # Other errors, below
                    raise
    
            # ######################################################################
            # THERE IS NEW DATA
            # ######################################################################
            n = len(data)
            if(DEBUG) : print(f"pkt len={n} -> {list(data)}")
            if(DEBUG) : print(data) # shows button pressed array
            pressed = None 

            if n < 7:
                short_streak += 1
                if short_streak >= 5:
                    if DEBUG: print("Too many short frames; reinit interface 1")
                    try:
                        usb.util.release_interface(dev, 1)
                    except Exception:
                        pass
                    dev.reset()
                    dev.set_configuration()
                    usb.util.claim_interface(dev, 1)
                    ep = dev[0].interfaces()[1].endpoints()[0]
                    short_streak = 0
                continue
            else:
                short_streak = 0

            # press types: 0 - up; 1 - down; 2 - hold
            press_type = 0

            # ##############################################################################################
            # Position & pressure_contact
            if n >= 7 and data[5] in [3,4,5,6]: #[192, 193]: # Pen actions
                pen_x = abs(max_x - (data[x1] * 255 + data[x2]))
                pen_y = abs(max_y - (data[y1] * 255 + data[y2]))
                pen_pressure = pressure_max - ( data[5] * 255 + data[6])
                if(DEBUG) : print("pen_x , pen_y : " , pen_x ,"-", pen_y , " --- pen_pressure :" , pen_pressure )
                if pen_pressure >= pressure_contact_threshold : # when Pen touches tablet surface detection value
                    if(DEBUG) : print("tablet tapped")
                    # ######################################################################################
                    # Here check wich button on top of the tablet is pressed
                    if pen_y>61200 :
                        press_type = 1
                        if pen_x==200 :
                            if(DEBUG) : print("mute")
                            pressed_prev=12
                        if pen_x==607 :
                            if(DEBUG) : print("vol-")
                            pressed_prev=13
                        if pen_x==1015 :
                            if(DEBUG) : print("vol+")
                            pressed_prev=14
                        if pen_x==1422 :
                            if(DEBUG) : print("note")
                            pressed_prev=15
                        if pen_x==1829 :
                            if(DEBUG) : print("play/pause")
                            pressed_prev=16
                        if pen_x==2237 :
                            if(DEBUG) : print("prev")
                            pressed_prev=17
                        if pen_x==2644 :
                            if(DEBUG) : print("next")
                            pressed_prev=18
                        if pen_x==3052 :
                            if(DEBUG) : print("home")
                            pressed_prev=19
                        if pen_x==3459 :
                            if(DEBUG) : print("calc")
                            pressed_prev=20
                        if pen_x==3866 :
                            if(DEBUG) : print("Desk")
                            pressed_prev=21
                    else :
                        vpen.write(ecodes.EV_KEY, ecodes.BTN_TOOL_PEN, 1 )
                        #vpen.write(ecodes.EV_KEY, ecodes.BTN_TOUCH, 1 ) #ecodes.BTN_TOUCH not executed ever since src code mods from original driver.py
                        vpen.write(ecodes.EV_KEY, ecodes.BTN_MOUSE, 1 ) # ecodes.BTN_MOUSE works, while ecodes.BTN_TOUCH does not execute
                else:
                    vpen.write(ecodes.EV_KEY, ecodes.BTN_MOUSE, 0 ) # BTN_MOUSE up event
                vpen.syn()
                vpen.write(ecodes.EV_ABS, ecodes.ABS_X, pen_x)
                vpen.write(ecodes.EV_ABS, ecodes.ABS_Y, pen_y)
                vpen.write(ecodes.EV_ABS, ecodes.ABS_PRESSURE, pen_pressure)

            # ##############################################################################################
            # Side Buttons
            if n >= 13:
                key_pressed = (data[11], data[12])
            else:
                key_pressed = (255, 51)  # „brak klawisza”
            if(DEBUG) : print("--- key_pressed : " , key_pressed )

            pressed = button_map.get(key_pressed, None)
                                                                                                                
            # press types: 0 - up; 1 - down; 2 - hold
            #press_type = 0 #moved begin loop for upper buttons
            if key_pressed != (255,51) : # Key_code tuple when no keys pressed
                press_type = 1
                # TODO : [ADE] hold with timer - but usage?
                # if pressed_prev == pressed :   #2-hold is not working nicely
                #    press_type = 2
                pressed_prev = pressed
            
            if pressed_prev is not None:
                if(DEBUG) :
                    print("Key_pressed detected : ", pressed_prev , " :: ", config["actions"]["tablet_buttons"][pressed_prev] ,
                          " -- press type ( 0-up, 1-down , 2-hold) :", press_type )
                key_codes = config["actions"]["tablet_buttons"][pressed_prev].split("+")
                for key in key_codes:
                    act = ecodes.ecodes[key]
                    vbtn.write(ecodes.EV_KEY, act, press_type)

            # ##############################################################################################
            # BTN_STYLUS & BTN_STYLUS2
            if n >= 10:
                val = data[9]
                # check which button was pressed (0=lower, 1=upper) or None
                if   val == 4:  curr = 0
                elif val == 6:  curr = 1
                else:           curr = None

            # Event type: down (1) / up (0) / brak (None)
            if pen_pressed_prev is None and curr is not None:
                press_type = 1   # just pressed
                btn = curr
            elif pen_pressed_prev is not None and curr is None:
                press_type = 0   # just released
                btn = pen_pressed_prev
            else:
                press_type = None
                btn = None

            # If  event down or  up, send it to vpen
            if btn is not None and press_type is not None:
                codes = config["actions"]["pen_buttons"][btn].split("+")
                for key in codes:
                    code = ecodes.ecodes[key]
                    vpen.write(ecodes.EV_KEY, code, press_type)
                vpen.syn()

            # remember button state
            pen_pressed_prev = curr


            # Flush
            vpen.syn()
            vbtn.syn()

            # reset pen button
            #pen_button=0x02

            # ---------------------------------------------------------------
    
        except usb.core.USBTimeoutError:
            # Second case of timeout (USBTimeoutError in my version of PyUSB)
            idle_timeouts += 1
            delay = min(0.05, 0.001 * idle_timeouts)
            if DEBUG and idle_timeouts % 60 == 0:
                print(f"[USB] idle timeout x{idle_timeouts} (delay={delay:.3f}s)")
            time.sleep(delay)
            if idle_timeouts >= 600:
                if DEBUG: print("[USB] long idle – soft re-claim iface 1")
                try: usb.util.release_interface(dev, 1)
                except Exception: pass
                try: usb.util.claim_interface(dev, 1)
                except usb.core.USBError: pass
                ep = dev[0].interfaces()[1].endpoints()[0]
                idle_timeouts = 0
            continue
    
        except usb.core.USBError as e:
            # Critical USB errors (ie. 19 after sleep/hibernation – no device)
            err = getattr(e, "errno", None)
            if err is None and e.args:
                err = e.args[0]
            if err == 19:
                if DEBUG: print("[USB] Device gone (Errno 19). Reconnecting…")
                try: usb.util.release_interface(dev, 1)
                except Exception: pass
                try: usb.util.dispose_resources(dev)
                except Exception: pass
                # lets wait while device will return
                new_dev = None
                for _ in range(150):  # ok. 15 s
                    time.sleep(0.1)
                    new_dev = usb.core.find(idVendor=config["vendor_id"], idProduct=config["product_id"])
                    if new_dev is not None:
                        break
                if new_dev is None:
                    if DEBUG: print("[USB] Not found again – exiting.")
                    try: vpen.close()
                    except Exception: pass
                    try: vbtn.close()
                    except Exception: pass
                    raise Exception("Device has been disconnected and not found again")
                # full init (setup_device_for_full_area)
                dev = new_dev
                time.sleep(0.1)  # a little wait after re-numeration
                ep = setup_device_for_full_area(dev)
                idle_timeouts = 0
                continue
            else:
                # Other errors
                if DEBUG: print(f"[USB] Unexpected USBError: {e!r}")
                raise
    
        except KeyboardInterrupt:
            vpen.close()
            vbtn.close()
            sys.exit("\nDriver terminated successfully.")
    
        except Exception as e:
            # Other error messages – lets log and try again
            if DEBUG: print("[MAIN] Unexpected exception:", e)
            time.sleep(0.05)
            continue
