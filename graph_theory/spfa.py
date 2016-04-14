from collections import deque

def spfa(source, num_nodes, weights, neighbor_list, epsilon=10E-5):
    """Shortest Paths Fastests Algorithm - think optimized Bellman-Ford,

        Assumes nodes have numbers from 0 to num_nodes (inclusive).
        Returns two variables:
            success - true if no negative cycle
            distances - shortest distance from the source to each node
                        or None if negative cycle
        """
    # None is Infinity
    distance = [None] * num_nodes
    currently_in_queue = [False for i in range(num_nodes)]
    times_in_queue = [0 for _ in range(num_nodes)]
    predecessor = [None for _ in range(num_nodes)]
    q = deque()

    distance[source] = 0
    currently_in_queue[source] = True
    times_in_queue[source] = 1
    q.append(0)

    negative_cycle_exists = False

    while len(q) > 0 and not negative_cycle_exists:
        node = q.popleft()
        currently_in_queue[node] = False
        for neighbor in neighbor_list[node]:

            if (distance[neighbor] is None or
                        distance[neighbor] > distance[node] + weights[(node, neighbor)] + epsilon):
                predecessor[neighbor] = node

                distance[neighbor] = distance[node] + weights[(node, neighbor)]
                if not currently_in_queue[neighbor]:
                    currently_in_queue[neighbor] = True
                    times_in_queue[neighbor] += 1
                    if times_in_queue[neighbor] > num_nodes:
                        negative_cycle_exists = True
                        break
                    q.append(neighbor)

    if negative_cycle_exists:
        visited = [False for _ in range(num_nodes)]
        negative_cycle = None

        for node in range(num_nodes):
            if not visited[node]:
                # Here we are extracting cycle in predecessor graph.
                # If we find any cycle it is necessarily negative cycle
                # because predecessor graph cannot be cyclic otherwise.
                potential_cycle_node = node
                potential_cycle = []
                while predecessor[potential_cycle_node] is not None and not visited[predecessor[potential_cycle_node]]:
                    # print(str(predecessor[potential_cycle_node]) + '->' + str(potential_cycle_node) + ':' + str(weights[(predecessor[potential_cycle_node], potential_cycle_node)]))
                    potential_cycle_node = predecessor[potential_cycle_node]
                    potential_cycle.append(potential_cycle_node)
                    visited[potential_cycle_node] = True
                # If the predecessor of the last node was already visited in this run we have our cycle.
                # it is not necessary spanning the entire array (we could have "entered" on cycle through
                # simple path.
                if predecessor[potential_cycle_node] in potential_cycle:
                    # print(str(predecessor[potential_cycle_node]) + '->' + str(potential_cycle_node) + ':' + str(weights[(predecessor[potential_cycle_node], potential_cycle_node)]))
                    cycle_start_index = potential_cycle.index(predecessor[potential_cycle_node])
                    negative_cycle = list(reversed(potential_cycle[cycle_start_index:]))
                    break
                visited[node] = True

        assert negative_cycle is not None
        # print("NCycle size: " + str(len(negative_cycle)))
        return distance, negative_cycle
    else:
        return distance, None