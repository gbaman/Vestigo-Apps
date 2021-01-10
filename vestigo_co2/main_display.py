# CO2 monitoring system using a Pimoroni Display-o-Tron HAT
# for input/output and a USB CO2 sensor

import time
import datetime
import vestigo_client
from CO2Meter import *
from dothat import lcd, backlight, touch
import os
import configparser

# Setup variables from config file
config = configparser.ConfigParser()
config.read('/boot/air.ini')
vestigo_server_url = config['vestigo']['vestigo_server_url']
vestigo_node_id = config['vestigo']['vestigo_node_id']
locations = config['general']['locations'].split(",")
delay = int(config['general']['delay'])
pause = False
shutting_down = False
backlight_on = True

if 'current_location' in config['general']:
    vestigo_sensor_name = config['general']['current_location']
else:
    vestigo_sensor_name = locations[0]

client = vestigo_client.Vestigo(vestigo_server_url, vestigo_node_id)


# Helper function to replace normal backlight.rgb()
# Allows for disabling the backlight
def backlight_rgb(r, g, b):
    if backlight_on:
        backlight.rgb(r, g, b)


# Disable the backlight
@touch.on(touch.DOWN)
def down_button(channel, event):
    global backlight_on
    if backlight_on:
        backlight_on = False
        backlight.off()
    else:
        backlight_on = True
        backlight_rgb(128, 128, 128)


# Pause/unpause logging
@touch.on(touch.BUTTON)
def touch_button(channel, event):
    global pause
    if pause:
        pause = False
        backlight_rgb(0, 255, 0)
    else:
        pause = True
        backlight_rgb(255, 0, 255)


# Shutdown the Pi
@touch.on(touch.CANCEL)
def cancel_button(channel, event):
    global pause, shutting_down
    shutting_down = True
    pause = True
    backlight_rgb(255, 255, 255)
    write_to_display(" SHUTTING DOWN".ljust(16), "".ljust(16), "".ljust(16))
    time.sleep(2)
    write_to_display("NO PROGRAM".ljust(16), "RUNNING. PLEASE".ljust(16), "RESTART THE PI..".ljust(16))
    print("SHUTTING DOWN")
    os.system("shutdown now")


# Select previous location
@touch.on(touch.LEFT)
def touch_left(channel, event):
    global vestigo_sensor_name, pause
    pause = True
    backlight_rgb(255, 0, 255)
    location_index = locations.index(vestigo_sensor_name)
    if location_index > 0:
        vestigo_sensor_name = locations[location_index - 1]
        lcd.set_cursor_position(0, 0)
        lcd.write(vestigo_sensor_name.ljust(16))
        config['general']['current_location'] = vestigo_sensor_name
        with open('/boot/air.ini', "w+") as configfile:
            config.write(configfile)


# Select next location
@touch.on(touch.RIGHT)
def touch_left(channel, event):
    global vestigo_sensor_name, pause
    pause = True
    backlight_rgb(255, 0, 255)
    location_index = locations.index(vestigo_sensor_name)
    if location_index < len(locations) - 1:
        vestigo_sensor_name = locations[location_index + 1]
        lcd.set_cursor_position(0, 0)
        lcd.write(vestigo_sensor_name.ljust(16))
        config['general']['current_location'] = vestigo_sensor_name
        with open('/boot/air.ini', "w+") as configfile:
            config.write(configfile)


def write_to_display(line_1, line_2, line_3):
    if len(line_1) > 16 or len(line_2) > 16 or len(line_3) > 16:
        print("Lines too long!")
        print(f"{line_1} - {len(line_1)}")
        print(f"{line_2} - {len(line_2)}")
        print(f"{line_3} - {len(line_3)}")
        return
    lcd.clear()
    lcd.set_cursor_position(0, 0)
    lcd.write(line_1)
    lcd.set_cursor_position(0, 1)
    lcd.write(line_2)
    lcd.set_cursor_position(0, 2)
    lcd.write(line_3)


def write_co2_status(co2_value):
    if co2_value < 600:
        lcd.write(chr(3))
        backlight_rgb(0, 255, 0)
    elif co2_value < 1000:
        lcd.write(chr(2))
        backlight_rgb(255, 153, 0)
    else:
        lcd.write(chr(1))
        backlight_rgb(255, 0, 0)


arrow = [
    0b00000,
    0b00100,
    0b01110,
    0b10101,
    0b00100,
    0b00100,
    0b00100,
    0b00000,
]
sad = [
    0b00000,
    0b00000,
    0b01010,
    0b00000,
    0b00000,
    0b01110,
    0b10001,
    0b00000,
]
ok = [
    0b00000,
    0b00000,
    0b01010,
    0b00000,
    0b00000,
    0b11111,
    0b00000,
    0b00000,
]
happy = [
    0b00000,
    0b00000,
    0b01010,
    0b00000,
    0b10001,
    0b01110,
    0b00000,
    0b00000,
]

# Set up the icons
lcd.create_char(0, arrow)
lcd.create_char(1, sad)
lcd.create_char(2, ok)
lcd.create_char(3, happy)

# Set up the LCD display and show starting
lcd.set_contrast(50)
backlight_rgb(255, 0, 255)
lcd.clear()
lcd.set_cursor_position(0, 0)
lcd.write("Starting...")

# Wait the sensor to become ready
while True:
    try:
        print("Trying to get sensor...")
        sensor = CO2Meter("/dev/hidraw0")
        break
    except OSError:
        print("ERROR - Unable to access sensor!")
        backlight_rgb(255, 0, 0)
        write_to_display("Error", "No CO2 sensor", "detected")
        time.sleep(1)

time.sleep(1)
print("Starting CO2 monitor")

# Main loop
while True:
    try:
        data = sensor.get_data()
    except OSError:
        print("Unable to get sensor data")
        backlight_rgb(255, 0, 0)
        write_to_display("Error", "Unable to get", "sensor data!")
        time.sleep(1)
        continue  # If sensor dies mid way, keep trying until it comes back

    if 'co2' in data:
        print(f"Data sent to server for co2 of {data['co2']}")
        status = client.log_sensor(f"{vestigo_sensor_name}-CO2", data['co2'])
        time.sleep(0.2)
    else:
        print("No CO2 data reported")
        time.sleep(1)
        continue  # If the data itself is empty, try again
    if 'temperature' in data:
        print(f"Data sent to server for temperature of {round(data['temperature'], 2)}")
        status = client.log_sensor(f"{vestigo_sensor_name}-Temperature", round(data['temperature'], 2))
        if status:
            # backlight_rgb(0, 255, 0)
            write_to_display(f"{vestigo_sensor_name}", f" {datetime.datetime.now().strftime('%H:%M:%S')}",
                             f"C:{str(data['co2']).zfill(4)}    T:{round(data['temperature'], 1)}")

            # Display upload arrow
            lcd.set_cursor_position(0, 1)
            lcd.write(chr(0))
            lcd.set_cursor_position(9, 1)
            lcd.write(chr(0))

            # Display happy/ok/sad face
            lcd.set_cursor_position(7, 2)
            write_co2_status(int(data['co2']))
            lcd.set_cursor_position(8, 2)
            write_co2_status(int(data['co2']))
        else:
            write_to_display(f"{vestigo_sensor_name}", f"No internet", f"C:{str(data['co2']).zfill(4)}    T:{round(data['temperature'], 1)}")

            # Display happy/ok/sad face
            lcd.set_cursor_position(7, 2)
            write_co2_status(int(data['co2']))
            lcd.set_cursor_position(8, 2)
            write_co2_status(int(data['co2']))
    else:
        print("No Temp data reported")
        time.sleep(1)
        continue

    # Countdown timer until next upload
    for seconds_left in range(0, delay):
        time.sleep(1)
        lcd.set_cursor_position(11, 1)
        lcd.write(f"  {str(delay - seconds_left).zfill(3)}")
        while pause:
            if not shutting_down:
                lcd.set_cursor_position(11, 1)
                lcd.write("PAUSE")
                time.sleep(1)
