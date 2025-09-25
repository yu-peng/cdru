__author__ = 'yupeng'

import math
from enum import Enum
from typing import Set, Dict, List, Optional


class EpisodeType(Enum):
    ACTIVITY = "ACTIVITY"
    CONSTRAINT = "CONSTRAINT"


class Event:
    """Represents an event in the temporal network."""
    
    def __init__(self, event_id: str, name: str = None):
        self.id = event_id
        self.name = name if name else event_id
        self.scheduled_time = 0.0
        self.is_scheduled = False
    
    def set_scheduled_time(self, time: float):
        """Set the scheduled time for this event."""
        self.scheduled_time = time
        self.is_scheduled = True
    
    def get_scheduled_time(self) -> float:
        """Get the scheduled time for this event."""
        return self.scheduled_time


class Episode:
    """Represents an episode (temporal constraint) in the network."""
    
    def __init__(self, episode_id: str, from_event: Event, to_event: Event, 
                 lower_bound: float, upper_bound: float, episode_type: EpisodeType = EpisodeType.CONSTRAINT):
        self.id = episode_id
        self.from_event = from_event
        self.to_event = to_event
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound
        self.type = episode_type
    
    def get_from_event(self) -> Event:
        return self.from_event
    
    def get_to_event(self) -> Event:
        return self.to_event
    
    def get_lb(self) -> float:
        return self.lower_bound
    
    def get_ub(self) -> float:
        return self.upper_bound
    
    def set_lb(self, lb: float):
        self.lower_bound = lb
    
    def set_ub(self, ub: float):
        self.upper_bound = ub


def schedule(episodes, start_event):
    """
    Schedule events using Bellman-Ford algorithm to find shortest paths to start of day.
    
    Args:
        candidate: A candidate solution with episodes and problem information
    """
    events = set()
    
    # First, collect all events from activated episodes
    for episode in episodes:
        events.add(episode.get_from_event())
        events.add(episode.get_to_event())
    
    # If no episodes, return early
    if not events:
        return
        
    start_idx = -1
    event_index_map = {}
    count = 0
    
    # Create mapping from events to indices
    for event in events:
        event_index_map[event] = count
        count += 1
    
    start_idx = event_index_map.get(start_event)
    if start_idx is None:
        return
    
    # Calculate shortest path TO the start of day using Bellman-Ford
    # We reverse the edges to find distance TO the start
    distance_to_start = [float('inf')] * len(events)
    distance_to_start[start_idx] = 0
    
    # Relax edges V-1 times
    changed = False
    for i in range(len(events) - 1):
        changed = False
        for episode in episodes:
            from_idx = event_index_map.get(episode.get_from_event())
            to_idx = event_index_map.get(episode.get_to_event())
            
            if from_idx is None or to_idx is None:
                continue
            
            # Flipping edges to find distance TO start
            if distance_to_start[to_idx] + episode.get_ub() - distance_to_start[from_idx] < 0:
                distance_to_start[from_idx] = distance_to_start[to_idx] + episode.get_ub()
                changed = True
            
            # Flipping edges to find distance TO start  
            if distance_to_start[from_idx] - episode.get_lb() - distance_to_start[to_idx] < 0:
                distance_to_start[to_idx] = distance_to_start[from_idx] - episode.get_lb()
                changed = True
        
        if not changed:
            break
    
    # Finally, schedule the events
    for event in events:
        d2sod = distance_to_start[event_index_map.get(event)]
        # SoD should always be the first event, and already scheduled, so just schedule the rest
        # distance to start is actually the lower edge of the STC SoD->E, so -d2sod is the earliest time after SoD
        if not event.is_scheduled:
            event.set_scheduled_time(round(start_event.get_scheduled_time() - d2sod))
    
    # Update the lower and upper bounds of activities in the solution
    for episode in episodes:
        if episode.type == EpisodeType.ACTIVITY:
            episode.set_lb(episode.get_to_event().get_scheduled_time() - episode.get_from_event().get_scheduled_time())
            episode.set_ub(episode.get_to_event().get_scheduled_time() - episode.get_from_event().get_scheduled_time())


# Example usage and helper functions
def create_example_scheduling_problem():
    """Create an example candidate with some test data."""
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from search.candidate import Candidate
    
    # Create some example events
    start_event = Event("start", "Start of Day")
    start_event.set_scheduled_time(0.0)
    
    event1 = Event("event1", "Event 1")
    event2 = Event("event2", "Event 2")
    event3 = Event("event3", "Event 3")
    
    # Create some example episodes
    episode1 = Episode("ep1", start_event, event1, 5.0, 10.0, EpisodeType.ACTIVITY)
    episode2 = Episode("ep2", event1, event2, 3.0, 8.0, EpisodeType.CONSTRAINT)
    episode3 = Episode("ep3", event2, event3, 2.0, 5.0, EpisodeType.ACTIVITY)
    
    return [episode1, episode2, episode3], start_event


if __name__ == "__main__":
    # Example usage
    episodes, start_event = create_example_scheduling_problem()
    schedule(episodes, start_event)
    
    print("Scheduling completed!")
    print("Events scheduled:")
    for episode in episodes:
        print(f"Episode {episode.id}: {episode.from_event.name} -> {episode.to_event.name}")
        print(f"  From event scheduled at: {episode.from_event.get_scheduled_time()}")
        print(f"  To event scheduled at: {episode.to_event.get_scheduled_time()}")
        if episode.type == EpisodeType.ACTIVITY:
            print(f"  Activity duration: {episode.get_lb()} - {episode.get_ub()}")
