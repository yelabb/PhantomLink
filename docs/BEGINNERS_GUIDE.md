# 🎓 PhantomLink: Complete Beginner's Guide

*A comprehensive, educational guide to understanding brain-computer interfaces and neural data streaming*

---

## 📚 Table of Contents

1. [What is PhantomLink?](#what-is-phantomlink)
2. [Brain-Computer Interfaces 101](#brain-computer-interfaces-101)
3. [Understanding Neural Channels](#understanding-neural-channels)
4. [Understanding Trials](#understanding-trials)
5. [Understanding Targets](#understanding-targets)
6. [Understanding Packets](#understanding-packets)
7. [How It All Fits Together](#how-it-all-fits-together)
8. [Real-World Applications](#real-world-applications)
9. [Technical Deep Dive](#technical-deep-dive)
10. [Learning Resources](#learning-resources)

---

## What is PhantomLink?

### The Simple Explanation

**PhantomLink is like a "practice server" for brain-computer interfaces.**

Imagine you're building an app that needs to process emails, but you don't want to use real user emails during development. You'd use a service like [Mailtrap](https://mailtrap.io/) or [Ethereal](https://ethereal.email/) - they let you send and receive fake emails for testing.

**PhantomLink does the same thing, but for brain signals!**

Instead of connecting to someone's actual brain implant, developers can use PhantomLink to stream pre-recorded brain activity. This lets them:
- Build and test brain-reading algorithms safely
- Train AI models without needing live subjects
- Develop BCI applications faster and cheaper
- Learn how brain signals work without specialized equipment

### What PhantomLink Does

```
Real BCI Setup:
Brain → Implant → Computer → Your Decoder → Action

PhantomLink Setup:
Recorded Brain Data → PhantomLink Server → Your Decoder → Action
```

PhantomLink replays **real neural recordings** at exactly 40 times per second (40Hz), just like they were recorded during an actual experiment. This gives developers realistic data to work with.

---

## Brain-Computer Interfaces 101

### What is a Brain-Computer Interface (BCI)?

A **BCI** is a direct connection between your brain and a computer. It reads brain activity and translates it into commands.

**Real-World Example:**
- Someone with paralysis has a chip implanted in their motor cortex (the part of the brain that controls movement)
- When they *think* about moving their hand, neurons in their motor cortex fire
- The chip records these neural signals
- A computer translates those signals into cursor movements on a screen
- The person can control a computer cursor just by thinking!

### Famous BCI Examples

1. **Neuralink** (Elon Musk's company) - Developing high-bandwidth brain implants
2. **BrainGate** - Helping paralyzed individuals control robotic arms
3. **Synchron** - Brain implant that doesn't require open brain surgery
4. **Facebook/Meta** - Working on non-invasive BCIs

### The Challenge

Building BCIs is hard because:
- **Ethics**: You can't just experiment on people's brains
- **Cost**: Brain implants and experiments are extremely expensive
- **Time**: It takes years to collect enough data
- **Access**: Very few research teams have access to live neural recordings

**This is where PhantomLink helps!** It democratizes BCI development by providing real brain data that anyone can use.

---

## Understanding Neural Channels

### The Biology

Your brain has about **86 billion neurons** (brain cells). When you think, move, or sense something, these neurons communicate by sending electrical signals called "action potentials" or "spikes."

### What is a Neural Channel?

A **neural channel** is like a **tiny microphone** placed in your brain to listen to these electrical signals.

**Analogy: Concert Hall**
```
🎸 Guitarist playing     = One neuron firing
🎤 Microphone           = One neural channel (electrode)
🎙️ 142 microphones      = 142 neural channels
🎵 Recording of concert  = Dataset we're using
```

### In the MC_Maze Dataset

- **142 neural channels** = 142 tiny electrodes implanted in the motor cortex
- Each electrode is about the width of a human hair
- They're arranged in an array (like a tiny grid) in the brain
- Each records activity from several neurons nearby

### What Does a Channel Record?

Every 25 milliseconds (40 times per second), each channel counts:
- **How many neurons fired** near that electrode
- This is called a "spike count"

Example:
```
Channel 1: 3 spikes   (3 neurons fired nearby)
Channel 2: 0 spikes   (no activity)
Channel 3: 7 spikes   (very active!)
...
Channel 142: 2 spikes
```

### Why Multiple Channels?

Different neurons control different aspects of movement:
- Some neurons fire when you move **left**
- Some fire when you move **right**
- Some fire based on **speed**
- Some fire based on **force**

By recording from 142 channels simultaneously, we capture a rich "picture" of what the brain is planning to do.

**More channels = Better predictions = More accurate BCI**

---

## Understanding Trials

### What is a Trial?

A **trial** is **one complete attempt** at a task - from start to finish.

### Sports Analogy

Think of basketball free throws:
```
Trial 1: 🏀 → 🎯 (Made it! ✅)
Trial 2: 🏀 → 🎯 (Made it! ✅)
Trial 3: 🏀 → ❌ (Missed 💥)
Trial 4: 🏀 → 🎯 (Made it! ✅)
```

Each throw is one trial. In our dataset, each trial is one reach toward a target.

### Trial Structure

```
🚦 START (t=0s)
   ↓
   Subject sees which target to reach for
   ↓
🧠 PLANNING
   ↓
   Brain activity increases (neurons start firing)
   ↓
🏃 MOVEMENT
   ↓
   Hand/cursor moves toward target
   ↓
🎯 TARGET REACHED (t=~3s)
   ↓
✅ END
```

### In the MC_Maze Dataset

- **100 trials total**
- Average duration: **2.88 seconds** per trial
- **100% success rate** (all reaches were successful)
- Trials are back-to-back (one ends, next begins)

### Why Trials Matter

**1. Structure**
Trials break up continuous recording into meaningful chunks. Instead of "5 minutes of random brain activity," you have "100 organized attempts."

**2. Labels**
Each trial has a label (which target was reached). This is crucial for training AI:
```
Trial 5: Target 0 → Brain signals → Used to teach AI "this is what Target 0 looks like"
Trial 6: Target 1 → Different signals → "this is what Target 1 looks like"
```

**3. Variety**
Different trials = different movements = more diverse training data

**4. Analysis**
You can analyze:
- Success rates
- Reaction times
- Learning curves (do they get faster?)
- Neural patterns per target

---

## Understanding Targets

### What is a Target?

A **target** is a **physical location** the subject is trying to reach.

### The Experiment Setup

Imagine a screen with dots arranged in a pattern:

```
        🎯 Target 2
       (top center)
           ↑
           |
🎯 Target 0 ← 🏠 → 🎯 Target 1
 (center)  Start  (right)
```

In the MC_Maze dataset:
- **3 targets** (Target 0, Target 1, Target 2)
- Positioned at different locations in 2D space
- Subject starts at center, reaches outward

### Center-Out Reaching Task

This is a **classic neuroscience experiment**:

1. Subject rests at center position
2. One target lights up (e.g., Target 1)
3. Subject moves toward that target
4. Target is reached → Trial complete!
5. Return to center, repeat

**Why this design?**
- Simple enough to repeat many times
- Complex enough to require planning
- Different directions activate different neurons
- Standardized task used across research labs

### Target Distribution

In our dataset:
```
Target 0: ████████████████████████████████████ 77 trials (most common)
Target 1: ████ 11 trials
Target 2: ████ 12 trials
```

Target 0 is likely the "home" or most frequently used position.

### Why Targets Matter for BCIs

**Directional Tuning:**
Neurons in motor cortex have "preferred directions." Some neurons fire more when you move:
- ⬆️ Up
- ➡️ Right  
- ⬇️ Down
- ⬅️ Left

By recording trials to different targets, we can:
1. Figure out each neuron's preferred direction
2. Build a decoder that understands "these neurons firing = moving right"
3. Predict intended movement direction from brain activity

**This is the core of how BCIs work!**

---

## Understanding Packets

### What is a Packet?

A **packet** is **one snapshot of brain activity** at a single moment in time.

### The Movie Analogy

Think of a movie:
```
🎬 Movie = The entire recording (293.7 seconds)
🎞️ Frame = One packet (1/40th of a second)
📹 Frame rate = 40 FPS (frames per second)
```

Just like a movie is made of many frames played back quickly, the neural recording is made of many packets streamed at 40Hz.

### What's in a Packet?

Each packet contains a **complete snapshot** of everything happening at that moment:

```json
{
  "timestamp": 1.525,           // Time: 1.525 seconds
  "sequence_number": 61,         // This is packet #61
  
  "spikes": {
    "channel_ids": [0, 1, 2, ..., 141],
    "spike_counts": [3, 0, 7, 2, ...]  // Activity on all 142 channels
  },
  
  "kinematics": {
    "vx": -8.383,                // Hand moving left at 8.383 units/s
    "vy": -4.490,                // Hand moving down at 4.490 units/s
    "x": -112.5,                 // Current X position
    "y": -87.3                   // Current Y position
  },
  
  "intention": {
    "target_id": 0,              // Reaching for Target 0
    "target_x": -120.0,          // Target is at X=-120
    "target_y": -90.0            // Target is at Y=-90
  },
  
  "trial_id": 10                 // This is from Trial 10
}
```

### The 40Hz Streaming Rate

**Why 40Hz?**
- **Fast enough** to capture rapid neural changes
- **Slow enough** to process in real-time
- **Standard rate** used in many BCI studies
- **25ms intervals** = 0.025 seconds between packets

**Timing is critical!** BCIs need to respond quickly:
```
Too slow (10Hz):   Laggy, cursor jerks
Just right (40Hz): Smooth, natural control
Too fast (1000Hz): Unnecessary, hard to process
```

### Packet Sequence

Packets are numbered continuously:
```
Packet 0    → Trial 0 starts
Packet 1    → 
Packet 2    →
...
Packet 136  → Trial 0 ends
Packet 137  → Trial 1 starts
Packet 138  →
...
Packet 11745 → Last packet, Trial 99 ends
```

### Why Packets Matter

**1. Real-Time Processing**
BCIs must work in real-time. Packets let you process data as it arrives:
```
Packet arrives → Run decoder → Predict movement → Update cursor
(All within 25ms!)
```

**2. Streaming Architecture**
Modern BCIs stream data over networks (WebSockets). Packets are the unit of transmission.

**3. Synchronization**
The `sequence_number` ensures packets aren't lost or out-of-order.

**4. Ground Truth**
Each packet includes what the subject *actually did* (kinematics) vs. what they *intended* (target). This lets you validate your decoder.

---

## How It All Fits Together

### The Complete Hierarchy

```
📦 Dataset: MC_Maze
│
├── 🧠 Neural Channels: 142
│   └── Each channel records nearby neuron activity
│
├── 🎯 Targets: 3
│   ├── Target 0 (center, most common)
│   ├── Target 1 (right)
│   └── Target 2 (top)
│
├── 📋 Trials: 100
│   ├── Trial 0: Reach to Target 0 (3.42s, 137 packets)
│   ├── Trial 1: Reach to Target 0 (2.13s, 85 packets)
│   ├── Trial 2: Reach to Target 0 (2.84s, 114 packets)
│   └── ...
│
└── 📡 Packets: 11,746 total
    ├── Packet 0: timestamp=0.000s, trial=0, target=0
    ├── Packet 1: timestamp=0.025s, trial=0, target=0
    └── ...
```

### Timeline Visualization

```
Time:     0s    1s    2s    3s    4s    5s    6s    7s    8s
          |-----|-----|-----|-----|-----|-----|-----|-----|
Trial 0:  [==========Target 0==========]
Packets:  ████████████████████████████████████████ (137 packets)
          
Trial 1:                               [====Target 0====]
Packets:                               ████████████████████ (85 packets)

Trial 2:                                                [=====Target 0======]
Packets:                                                ███████████████████████ (114 packets)
```

Each `█` represents one packet (25ms of data).

### Data Flow in PhantomLink

```
1. LOADING
   NWB File → MC_MazeLoader → Parse structure

2. ORGANIZATION  
   Raw data → Organize by trials, targets, channels

3. STREAMING
   Request arrives → PlaybackEngine → Generate packet

4. DELIVERY
   Packet → JSON → WebSocket → Your decoder

5. DECODING (your code!)
   Packet → Feature extraction → ML model → Prediction
```

### Filtering Options

PhantomLink lets you filter the stream:

**By Target:**
```
ws://localhost:8000/stream?target_id=0
→ Only get packets when reaching for Target 0
→ Useful for training direction-specific decoders
```

**By Trial:**
```
ws://localhost:8000/stream?trial_id=42
→ Only get packets from Trial 42
→ Useful for analyzing specific movements
```

**All Data:**
```
ws://localhost:8000/stream
→ Get everything in order
→ Useful for full dataset analysis
```

---

## Real-World Applications

### 1. Assistive Technology

**For Paralyzed Individuals:**
- Control computer cursor with thoughts
- Type messages using on-screen keyboard
- Control smart home devices
- Operate robotic arms
- Drive wheelchairs

**PhantomLink helps by:**
- Letting developers build and test control algorithms
- Training AI models without needing live subjects
- Iterating quickly on decoder designs

### 2. Prosthetics

**Robotic Limbs:**
- Natural control of prosthetic arms/hands
- Fine motor control (grasping, pointing)
- Sensory feedback integration

**PhantomLink helps by:**
- Simulating different movement intentions
- Testing control algorithms for different gestures
- Validating real-time performance

### 3. Communication

**For People Who Can't Speak:**
- Direct brain-to-text
- Thought-to-speech synthesis
- High-speed communication

**Example:** A person with ALS can "type" at 90 characters per minute using only brain signals!

### 4. Research

**Neuroscience Studies:**
- Understanding how the brain encodes movement
- Studying neural plasticity
- Mapping brain function

**PhantomLink helps by:**
- Providing accessible research-grade data
- Enabling reproducible experiments
- Teaching students about neural coding

### 5. Gaming & VR

**Future Applications:**
- Control games with thoughts
- Enhanced VR immersion
- Brain-based authentication

### 6. Medicine

**Clinical Applications:**
- Seizure prediction
- Parkinson's treatment optimization
- Stroke rehabilitation monitoring

---

## Technical Deep Dive

### The Dataset: Neural Latents Benchmark

**Source:** [Neural Latents Benchmark](https://neurallatents.github.io/)  
**Dataset:** MC_Maze (Motor Cortex, Maze Task)

**Recording Details:**
- **Subject:** Non-human primate (monkey)
- **Implant:** Utah array (10×10 electrode grid)
- **Location:** Primary motor cortex (M1)
- **Task:** Center-out reaching with cursor
- **Recording Duration:** 293.7 seconds (~5 minutes)
- **Sampling Rate:** Behavior at 40Hz, neural spikes timestamped

**Data Format:**
- Stored in NWB (Neurodata Without Borders) format
- HDF5-based file structure
- Contains neural, behavioral, and trial metadata

### How PhantomLink Works

**Architecture:**
```
┌─────────────┐
│  NWB File   │ (Raw data)
└──────┬──────┘
       │
       ↓
┌─────────────────┐
│ MC_MazeLoader   │ (Lazy loading, memory mapping)
└────────┬────────┘
         │
         ↓
┌──────────────────┐
│ PlaybackEngine   │ (40Hz packet generation)
└────────┬─────────┘
          │
          ↓
┌─────────────────┐
│ FastAPI Server  │ (HTTP + WebSocket endpoints)
└────────┬────────┘
          │
          ↓
┌─────────────────┐
│ Your Decoder    │ (Receives packets, makes predictions)
└─────────────────┘
```

**Key Technologies:**
- **FastAPI:** Modern Python web framework
- **WebSockets:** Real-time bi-directional communication
- **PyNWB:** Reading neuroscience data files
- **NumPy:** Efficient numerical computations
- **Asyncio:** Concurrent request handling

### Packet Generation Process

**Step-by-step:**

1. **Client connects** to WebSocket endpoint
2. **PlaybackEngine** starts at index 0
3. **Every 25ms:**
   ```python
   # Calculate time window
   start_time = index * 0.025
   end_time = start_time + 0.025
   
   # Extract neural data
   spikes = loader.get_binned_spikes(start_time, end_time)
   
   # Extract behavioral data
   kinematics = loader.get_kinematics(start_time, end_time)
   
   # Get trial context
   trial_info = loader.get_trial_by_time(start_time)
   
   # Build packet
   packet = StreamPacket(
       timestamp=current_time,
       sequence_number=index,
       spikes=spikes,
       kinematics=kinematics,
       intention=trial_info,
       trial_id=trial_info.id
   )
   
   # Send over WebSocket
   await websocket.send_json(packet.dict())
   
   index += 1
   ```

4. **Repeat** until dataset ends or client disconnects

### Session Management

PhantomLink uses a **ChatGPT-style architecture:**

```
Client 1: /session/create
          → Gets unique session ID: "neural-ace-42"
          → Stream URL: ws://localhost:8000/stream/neural-ace-42

Client 2: /session/create  
          → Gets unique session ID: "swift-neural-17"
          → Stream URL: ws://localhost:8000/stream/swift-neural-17
```

**Benefits:**
- Multiple users can test simultaneously
- Each gets independent playback
- Shareable URLs for collaboration
- Isolated state per session

---

## Learning Resources

### Recommended Reading

**For Complete Beginners:**
1. "Brain-Computer Interfaces: Principles and Practice" - Wolpaw & Wolpaw
2. "Neuronal Dynamics" - Gerstner et al. (free online)
3. Khan Academy: Neuroscience basics

**For Developers:**
1. Neural Latents Benchmark documentation
2. PyNWB tutorials
3. FastAPI documentation
4. This repository's code!

### Online Courses

1. **Coursera:** Computational Neuroscience (University of Washington)
2. **edX:** Fundamentals of Neuroscience (Harvard)
3. **YouTube:** 3Blue1Brown's Neural Networks series

### Research Papers

**Classic Papers:**
1. Georgopoulos et al. (1982) - "Neuronal population coding of movement direction"
2. Hochberg et al. (2006) - "Neuronal ensemble control of prosthetic devices by a human with tetraplegia"

**Modern Reviews:**
1. Willett et al. (2021) - "High-performance brain-to-text communication via handwriting"
2. Neural Latents Benchmark paper

### Datasets & Tools

1. **Neural Latents Benchmark** - Multiple motor cortex datasets
2. **NWB Explorer** - Visualize NWB files
3. **CRCNS** - Collaborative Research in Computational Neuroscience datasets

### Communities

1. **Reddit:** r/neuroscience, r/neuroengineering
2. **Discord:** NeuroTech Berkeley, BrainAI
3. **Twitter:** #BCI, #neuroscience, #neurotech

### Hands-On Projects

**Start Here:**
1. Run PhantomLink locally
2. Open the [data_analysis.ipynb](data_analysis.ipynb) notebook
3. Build a simple linear decoder
4. Try filtering by target and compare accuracy

**Next Steps:**
1. Implement a Kalman filter decoder
2. Add real-time visualization
3. Build a cursor control demo
4. Train a neural network decoder

---

## Common Questions

### Q: Do I need neuroscience knowledge to use PhantomLink?

**A:** No! While it helps, PhantomLink is designed to be accessible. This guide covers everything you need to get started.

### Q: Can I use this data for my own projects?

**A:** Yes! The MC_Maze dataset is publicly available for research and educational purposes. Check the Neural Latents Benchmark license.

### Q: Is this data from humans?

**A:** No, it's from a non-human primate (monkey). Human BCI data is much more restricted due to privacy and ethics.

### Q: How accurate are current BCIs?

**A:** Modern research BCIs can achieve:
- **Cursor control:** 90%+ accuracy
- **Typing:** 90 characters/minute
- **Robotic arm control:** Smooth, natural movements

But there's still much room for improvement!

### Q: What programming languages do I need?

**A:** Python is the primary language. You should know:
- Basic Python syntax
- NumPy for arrays
- Basic async/await (for WebSockets)

### Q: How much data does PhantomLink stream?

**A:** About 50-100 KB per second, depending on the number of channels. Very manageable for modern networks.

### Q: Can I add my own datasets?

**A:** Not directly, but you can fork PhantomLink and adapt the DataLoader for your NWB files!

### Q: What machine learning models work best?

**A:** Common approaches:
- **Kalman Filter** (classic, simple, fast)
- **Linear Regression** (surprisingly effective baseline)
- **RNNs/LSTMs** (capture temporal dynamics)
- **Transformers** (state-of-the-art, but overkill for many tasks)

Start simple, then add complexity as needed!

---

## Next Steps

### 1. Get Started

```bash
# Clone the repository
git clone https://github.com/yelabb/PhantomLink.git
cd PhantomLink

# Install dependencies
pip install -r requirements.txt

# Run the server
python server.py

# Open the data analysis notebook
jupyter notebook data_analysis.ipynb
```

### 2. Explore the Data

- Run all cells in `data_analysis.ipynb`
- Look at the visualizations
- Understand the packet structure

### 3. Build Your First Decoder

Start with a simple project:
```python
# Pseudo-code for a basic decoder
async def simple_decoder():
    async with websockets.connect("ws://localhost:8000/stream") as ws:
        while True:
            packet = await ws.recv_json()
            
            # Extract features (simplified)
            spike_counts = packet['spikes']['spike_counts']
            avg_activity = np.mean(spike_counts)
            
            # Predict (simplified)
            if avg_activity > threshold:
                print("Moving!")
            else:
                print("Resting")
```

### 4. Join the Community

- Star this repository ⭐
- Join neuroscience/BCI communities
- Share your projects
- Contribute improvements

---

## Glossary

**Action Potential** - Electrical signal that travels along a neuron (also called a "spike")

**BCI** - Brain-Computer Interface; direct connection between brain and computer

**Decoder** - Algorithm that translates brain signals into intended actions

**Electrode** - Tiny sensor that records electrical activity in the brain

**Kinematics** - Description of motion (position, velocity, acceleration)

**M1** - Primary motor cortex; brain region that controls voluntary movement

**Neural Channel** - One recording site/electrode in a brain implant

**NWB** - Neurodata Without Borders; standard format for neuroscience data

**Packet** - Single snapshot of brain activity and behavior at one moment

**Spike** - Brief electrical signal from a neuron (action potential)

**Target** - Location the subject is trying to reach

**Trial** - One complete attempt at the task

**Utah Array** - Grid of 100 electrodes implanted in the brain

---

## Conclusion

PhantomLink makes BCI development accessible to everyone. Whether you're a:
- 🎓 **Student** learning about neuroscience
- 👨‍💻 **Developer** building BCI applications
- 🔬 **Researcher** studying neural coding
- 🤔 **Curious person** wanting to understand brains

...you now have the tools and knowledge to explore real brain data!

**Remember:** Every major technology started with people like you experimenting and learning. Today's educational project could become tomorrow's life-changing BCI application.

---

**Questions? Found a bug? Want to contribute?**

Open an issue on [GitHub](https://github.com/yelabb/PhantomLink) or check out the [main README](README.md)!

---

*Last updated: January 12, 2026*  
*Made with 🧠 and ❤️ for the neuroscience community*
