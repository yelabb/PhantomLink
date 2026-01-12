"""Investigate NWB file structure to understand data extraction issues."""
from pynwb import NWBHDF5IO
import numpy as np

io = NWBHDF5IO('data/mc_maze.nwb', 'r')
nwb = io.read()
units = nwb.units

print('=== NWB Units Structure ===')
print(f'Total units: {len(units.id[:])}')
print(f'spike_times type: {type(units["spike_times"])}')
print(f'spike_times_index type: {type(units["spike_times_index"])}')
print()

print('=== Testing Access Pattern ===')
for i in range(10):
    st = units['spike_times'][i]
    print(f'Unit {i}: {len(st)} spikes, first: {st[0]:.4f}s, last: {st[-1]:.4f}s')
print()

print('=== Checking time windows ===')
# Test extracting spikes in a time window
start_time = 0.0
end_time = 0.025  # 25ms window
print(f'Testing window [{start_time}, {end_time}]')
for i in range(5):
    spike_times = units['spike_times'][i]
    mask = (spike_times >= start_time) & (spike_times < end_time)
    spikes_in_window = spike_times[mask]
    print(f'  Unit {i}: {len(spikes_in_window)} spikes in window')
print()

print('=== Checking Behavioral Data ===')
behavior = nwb.processing['behavior']
print(f'Behavior module: {list(behavior.data_interfaces.keys())}')
cursor = behavior['cursor_pos']
hand = behavior['hand_vel']
print(f'cursor_pos shape: {cursor.data.shape}')
print(f'hand_vel shape: {hand.data.shape}')
print(f'cursor timestamps shape: {cursor.timestamps.shape}')
print(f'Sample cursor data (first 3):')
print(cursor.data[:3])
print(f'Sample cursor timestamps (first 3):')
print(cursor.timestamps[:3])
print(f'Cursor sampling rate: {1.0 / np.mean(np.diff(cursor.timestamps[:100]))} Hz')
print()

print('=== Performance Test ===')
import time
# Test how long it takes to extract one packet worth of data
start = time.time()
for _ in range(100):
    start_time = 0.0
    end_time = 0.025
    for unit_idx in range(len(units.id[:])):
        spike_times = units['spike_times'][unit_idx]
        mask = (spike_times >= start_time) & (spike_times < end_time)
        spikes = spike_times[mask]
elapsed = time.time() - start
print(f'Time to extract 100 packets: {elapsed:.3f}s')
print(f'Average time per packet: {elapsed/100*1000:.2f}ms')
print(f'Expected time at 40Hz: 25ms')

io.close()
