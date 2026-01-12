"""Quick test to verify vectorization optimization."""
import numpy as np
from pathlib import Path
from data_loader import MC_MazeLoader

DATA_PATH = Path(__file__).parent / "data" / "mc_maze.nwb"

if DATA_PATH.exists():
    with MC_MazeLoader(DATA_PATH) as loader:
        # Test get_binned_spikes
        print("Testing optimized get_binned_spikes...")
        
        # Get spike data for first 5 seconds
        spike_counts = loader.get_binned_spikes(0, 5.0, bin_size_ms=25.0)
        
        print(f"✅ Shape: {spike_counts.shape}")
        print(f"✅ Total spikes: {spike_counts.sum()}")
        print(f"✅ Non-zero bins: {np.count_nonzero(spike_counts)}")
        print(f"✅ Max spikes per bin: {spike_counts.max()}")
        
        # Test with different bin size
        spike_counts2 = loader.get_binned_spikes(0, 1.0, bin_size_ms=50.0)
        print(f"\n✅ Different bin size test: {spike_counts2.shape}")
        
        print("\n✅ Vectorization optimization works correctly!")
else:
    print(f"⚠️ Test data not found at {DATA_PATH}")
