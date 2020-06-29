import os
import sys
import dgl
from dgl.data.utils import load_graphs
from dgl.nn.pytorch import GraphConv
import torch
import torch.nn as nn
import torch.nn.functional as f
import torch.optim as optim
from torch.utils.data import DataLoader
from sklearn import metrics
import numpy as np

from src.data.CNFDataset import CNFDataset


def collate(dev):
    def collate_fn(samples):
        """
            Forms a mini-batch from a given list of graphs and label pairs
            :param samples: list of tuple pairs (graph, label)
            :return:
            """
        graphs, labels = map(list, zip(*samples))
        batched_graph = dgl.batch(graphs)
        return batched_graph, torch.tensor(labels, device=dev, dtype=torch.float32)
    return collate_fn


class Regressor(nn.Module):
    def __init__(self, in_dim, hidden_dim, n_predicted_vals):
        super(Regressor, self).__init__()
        self.conv1 = GraphConv(in_dim, hidden_dim)
        self.conv2 = GraphConv(hidden_dim, hidden_dim)
        self.regress = nn.Linear(hidden_dim, n_predicted_vals)

    def forward(self, g: dgl.DGLGraph):
        # Use the node2vec data as initial node features
        h = g.ndata['features']
        h = f.relu(self.conv1(g, h))
        h = f.relu(self.conv2(g, h))
        g.ndata['h'] = h

        hg = dgl.mean_nodes(g, 'h')
        return self.regress(hg)


# Train the model
def train(device):
    # Load train data
    csv_file_x = os.path.join(os.path.dirname(__file__),
                              '..', '..', 'INSTANCES', 'chosen_data', 'max_vars_5000_max_clauses_200000.csv')
    csv_file_y = os.path.join(os.path.dirname(__file__),
                              '..', '..', 'INSTANCES', 'chosen_data', 'all_data_y.csv')
    root_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'INSTANCES')
    trainset = CNFDataset(csv_file_x, csv_file_y, root_dir)

    data_loader = DataLoader(trainset, batch_size=1, shuffle=True, collate_fn=collate(device))

    # Create model
    num_predicted_values = 31
    model = Regressor(2, 256, num_predicted_values)
    model.to(device)
    loss_func = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=1e-3)
    model.train()

    # Start training
    epochs = 100
    epoch_losses = []
    for epoch in range(epochs):
        epoch_loss = 0
        iter_idx = -1
        for iter_idx, (bg, label) in enumerate(data_loader):
            prediction = model(bg.to(device))
            loss = loss_func(prediction, label.to(device))
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            epoch_loss += loss.detach().item()
        epoch_loss /= (iter_idx + 1)
        print(f'Epoch {epoch}, loss {epoch_loss}')
        epoch_losses.append(epoch_loss)
    torch.save(model, os.path.join(os.path.dirname(__file__), '..', '..', 'models', 'gcn_model'))


# Test the model
def test():
    # TODO: Load test data
    test_graph_list, test_label_dict = load_graphs("./test.bin")
    test_bg = dgl.batch(test_graph_list)
    test_y = torch.tensor(map(list, test_label_dict))

    # Load the model
    model = torch.load(os.path.join(os.path.dirname(__file__), '..', '..', 'models', 'gcn_model'))
    model.eval()
    r2_scores = []
    rmse_scores = []

    # Evaluate
    for graph, true_y in zip(test_graph_list, test_label_dict):
        pred_y = model(graph)
        r2_score = metrics.r2_score(true_y, pred_y)
        r2_scores.append(r2_score)
        rmse_score = metrics.mean_squared_error(true_y, pred_y, squared=False)
        rmse_scores.append(rmse_score)

    print(f'R2: {np.average(r2_scores)}, RMSE: {np.average(rmse_scores)}')


if __name__ == "__main__":
    # Set the device
    # device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    device = torch.device("cpu")
    print(device)

    # Start training
    train(device)
