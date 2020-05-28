rm -rf ../trinity_data
python3 trinity/db/manager.py --trinity-root-dir "../trinity_data" -l 10 &>/dev/null &
sleep 5
python3 trinity/components/builtin/peer_discovery/component.py --trinity-root-dir "../trinity_data"
