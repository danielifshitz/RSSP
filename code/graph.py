from collections import defaultdict

class Graph:

    def __init__(self,vertices):
        self.V = vertices #No. of vertices - num of ops+2
        self.graph = [] # default 2 dim array  to store graph


    # function to add an edge to graph
    def addEdge(self,u,v,w):
        self.graph.append([u, v, w])


    def bellman_ford_LB(self,src,dest):
        # Initialize distances from src to all other vertices
        dist = [float("-Inf")] * self.V
        dist[src] = 0 # the s verticle

        # Update dist value and parent index of the adjacent vertices of the
        # picked vertex. Consider only those vertices which are still in queue
        for u, v, w in self.graph:
            if dist[u] != float("-Inf") and dist[u] + w > dist[v]:
                    dist[v] = dist[u] + w

        return dist[dest]
