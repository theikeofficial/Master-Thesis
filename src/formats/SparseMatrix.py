import numpy as np
from scipy import sparse
from src.formats.Edgelist import Edgelist


class SparseMatrix:
    def __init__(self):
        self.data: sparse.dok_matrix = None

    def from_edgelist(self, from_data: Edgelist):
        if from_data.max_node == -1:
            raise ValueError("Edgelist is not populated")
        self.data = sparse.dok_matrix((from_data.max_node + 1, from_data.max_node + 1), dtype=np.float)
        for i in range(len(from_data.data)):
            v1 = from_data.data[i][0]
            v2 = from_data.data[i][1]
            self.data[v1, v2] = 1