from collections import defaultdict

class Bellman_Ford:

    """
    this class present bellman_ford algorithm.
    using this algorithm we will find the LB value of the problem.
    """

    def __init__(self,vertices):
        self.V = vertices #No. of vertices - num of ops+2
        self.graph = [] # list to store the graph


    def addEdge(self,u,v,w):
        """
        add an edge to graph
        u: string, vertices name
        v: string, vertices name
        w: number, the wight on the edge between u and v
        return: None
        """
        self.graph.append([u, v, w])


    def bellman_ford_LB(self,src,dest):
        """
        cacolate the max distance from src vertices to dest vertices
        src: string, vertices name
        dest: string, vertices name
        return: the max distance from src vertices to dest vertices
        """
        # Initialize distances from src to all other vertices
        dist = [float("-Inf")] * self.V
        dist[src] = 0 # the s verticle

        # Update dist value and parent index of the adjacent vertices of the
        # picked vertex. Consider only those vertices which are still in queue
        for u, v, w in self.graph:
            if dist[u] != float("-Inf") and dist[u] + w > dist[v]:
                    dist[v] = dist[u] + w

        return dist[dest]
