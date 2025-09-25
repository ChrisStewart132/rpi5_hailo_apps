

## run web server script (rpi5)
python detection_server.py

## run rpi5 + ai hat (m2+ hailo8l) detection script
with hailo example apps installed
env enabled: source setup_env.sh
enable display: export DISPLAY=:0
cmd: python detection_client.py --input rpi

## open website to view (rpi5 local ip)
http://192.168.1.74:8000/