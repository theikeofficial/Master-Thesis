import os
from timeit import default_timer as timer

import dgl
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from dgl.nn.pytorch import GraphConv, SumPooling, MaxPooling, AvgPooling
from sklearn import metrics
from torch.utils.data import DataLoader
from matplotlib import pyplot as plt

from src.data.CNFDatasetNode2Vec import CNFDatasetNode2Vec
from src.utils.FileLogger import FileLogger

DatasetClass = CNFDatasetNode2Vec
csv_file_x = os.path.join(os.path.dirname(__file__),
                          '..', '..', 'INSTANCES', 'chosen_data', 'max_vars_5000_max_clauses_200000.csv')
csv_file_y = os.path.join(os.path.dirname(__file__),
                          '..', '..', 'INSTANCES', 'chosen_data', 'all_data_y.csv')
root_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'INSTANCES')


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


class RMSELoss(nn.Module):
    def __init__(self, eps=1e-6):
        super().__init__()
        self.mse = nn.MSELoss()
        self.eps = eps

    def forward(self, yhat, y):
        loss = torch.sqrt(self.mse(yhat, y) + self.eps)
        return loss


class Regressor(nn.Module):
    def __init__(self, input_dim, hidden_dim, output_dim, num_layers, activation, activation_params, dropout_p,
                 pooling="avg"):
        super(Regressor, self).__init__()

        # Checks
        if num_layers < 2:
            raise ValueError(f"Argument num_layers must be >= 2. You passed {num_layers}")

        if activation == "relu":
            self.activation = nn.ReLU(**activation_params)
        elif activation == "leaky":
            self.activation = nn.LeakyReLU(**activation_params)
        elif activation == "elu":
            self.activation = nn.ELU(**activation_params)
        elif activation == "selu":
            self.activation = nn.SELU(**activation_params)
        else:
            raise NotImplementedError(f"Unknown activation method: {pooling}")

        self.layers = nn.ModuleList()
        # Input layer
        self.layers.append(GraphConv(input_dim, hidden_dim))
        # Hidden layers
        for i in range(num_layers - 1):
            self.layers.append(GraphConv(hidden_dim, hidden_dim))

        # Additional layers
        if pooling == "avg":
            self.pool = AvgPooling()
        elif pooling == "sum":
            self.pool = SumPooling()
        elif pooling == "max":
            self.pool = MaxPooling()
        else:
            raise NotImplementedError(f"Unknown pooling method: {pooling}")

        self.linear = nn.Linear(hidden_dim, output_dim)
        self.dropout = nn.Dropout(p=dropout_p)

    def forward(self, g: dgl.DGLGraph):
        # Use the already set features data as initial node features
        h = g.ndata['features']
        # Apply layers
        for i, layer in enumerate(self.layers):
            if i != 0:
                h = self.dropout(h)
            h = layer(g, h)
            h = self.activation(h)

        # Perform pooling over all nodes in each graph in every layer
        pooled_h = self.pool(g, h)

        # Return the predicted data in linear layer over pooled data
        linear = self.linear(pooled_h)

        return linear


def train_one_epoch(data_loader_train, loss_func, model, optimizer, train_device):
    model.train()
    train_loss = 0
    iter_idx = 0
    for iter_idx, (bg, label) in enumerate(data_loader_train):
        # Predict
        prediction = model(bg.to(train_device))
        loss = loss_func(prediction, label.to(train_device))
        # Backprop
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        # Report loss
        train_loss += loss.detach().item()
    return np.round(train_loss / (iter_idx + 1), 3)


def validate_one_epoch(model, loss_func, data_loader_val, train_device, test_device):
    model.eval()
    val_loss = 0
    iter_num = 0
    y_pred = np.empty((0, 31))
    y_true = np.empty((0, 31))
    for iter_num, (bg, label) in enumerate(data_loader_val):
        prediction = model(bg.to(train_device))
        # Calculate loss
        loss = loss_func(prediction, label.to(train_device))
        val_loss += loss.detach().item()
        # Save prediction for calculating R^2 and RMSE scores
        pred_y = model(bg.to(train_device))
        pred_y = np.array(pred_y.to(test_device).detach().numpy())
        y_pred = np.vstack((y_pred, pred_y))
        y_true = np.vstack((y_true, label.to(test_device)))

    r2_score_val_avg, rmse_score_val_avg = calculate_r2_and_rmse_scores(y_pred, y_true)

    return np.round([val_loss / (iter_num + 1), r2_score_val_avg, rmse_score_val_avg], 3)


def calculate_r2_and_rmse_scores(y_pred, y_true):
    r2_scores_val = np.empty((31,))
    rmse_scores_val = np.empty((31,))

    for i in range(31):
        r2_scores_val[i] = metrics.r2_score(y_true[:, i:i + 1], y_pred[:, i:i + 1])
        rmse_scores_val[i] = metrics.mean_squared_error(y_true[:, i:i + 1], y_pred[:, i:i + 1], squared=False)

    r2_score_val_avg = np.average(r2_scores_val)
    rmse_score_val_avg = np.average(rmse_scores_val)

    return r2_score_val_avg, rmse_score_val_avg


# Train the model
def train(train_device, test_device):
    # Load train data
    trainset = DatasetClass(csv_file_x, csv_file_y, root_dir, "train")
    data_loader_train = DataLoader(trainset, batch_size=1, shuffle=True, collate_fn=collate(train_device))

    # Load val data
    valset = DatasetClass(csv_file_x, csv_file_y, root_dir, "val")
    data_loader_val = DataLoader(valset, batch_size=1, shuffle=True, collate_fn=collate(train_device))

    # Load train+val data
    trainvalset = DatasetClass(csv_file_x, csv_file_y, root_dir, "train+val")
    data_loader_trainval = DataLoader(trainvalset, batch_size=1, shuffle=True, collate_fn=collate(train_device))

    print("\n")

    # Model params
    input_dim = trainset.data_dim
    hidden_dim = 128
    output_dim = 31
    num_layers = 3
    activation = "elu"
    activation_params = {"alpha": 0.2}
    dropout_p = 0.3
    pooling = "avg"
    # Optimizer params
    lr = 1e-5
    w_decay = 1e-3
    loss = "mse"
    # Num of epochs
    epochs = 200
    no_progress_max = 5

    # Model name
    mfn = f'gcn_{hidden_dim}_{num_layers}_{dropout_p}_{pooling}_{activation}_{lr}_{w_decay}_{epochs}_{loss}'
    model_path = os.path.join(os.path.dirname(__file__), '..', '..', 'models', mfn)
    if os.path.exists(model_path):
        print("\nModel had already been trained!")
        return model_path
    
    # Create a logger
    log = FileLogger(mfn)

    log.log_bar()
    log.log_line(f"Model name: {mfn}")
    log.log_bar()
    log.log_line("Model parameters")
    log.log_bar()
    log.log_line(f"Features dimension: {input_dim}")
    log.log_line(f"Dimension of hidden layers: {hidden_dim}")
    log.log_line(f"Output dimension: {output_dim}")
    log.log_line(f"Number of hidden layers: {num_layers}")
    log.log_line(f"Activation function: {activation}")
    log.log_line(f"Activation function params: {activation_params}")
    log.log_line(f"Dropout: {dropout_p}")
    log.log_line(f"Pooling method: {pooling}")
    log.log_bar()
    log.log_line("Optimizer params (ADAM)")
    log.log_bar()
    log.log_line(f"Learning rate: {lr}")
    log.log_line(f"Weight decay: {w_decay}")
    log.log_line(f"Loss function: {loss}")
    log.log_bar()
    log.log_line(f"Maximum number of epochs: {epochs}")
    log.log_bar()

    # Create model
    model = Regressor(input_dim,
                      hidden_dim,
                      output_dim,
                      num_layers,
                      activation,
                      activation_params,
                      dropout_p,
                      pooling)
    model.to(train_device)
    if loss == "l1":
        loss_func = nn.L1Loss()
    elif loss == "mse":
        loss_func = nn.MSELoss()
    elif loss == "smooth-l1":
        loss_func = nn.SmoothL1Loss()
    elif loss == "rmse":
        loss_func = RMSELoss()
    else:
        raise ValueError(f"Loss function is not one of ['l1', 'mse', 'smooth-l1']. You passed: {loss}")
    optimizer = optim.Adam(model.parameters(), lr=lr, weight_decay=w_decay)
    log.log_line("\nModel created! Training...\n")

    # Start training
    train_losses = []
    val_losses = []
    r2_scores = []
    rmse_scores = []
    train_times = []
    val_times = []
    best_epoch = -1
    best_val_loss = None
    no_progress_count = 0
    for current_epoch in range(1, epochs + 1):
        # Train on training data
        time_start = timer()
        train_loss = train_one_epoch(data_loader_train, loss_func, model, optimizer, train_device)
        time_elapsed = timer() - time_start
        train_times.append(time_elapsed)
        train_losses.append(train_loss)

        # Validate on validating data
        time_start = timer()
        val_loss, r2_score_val_avg, rmse_score_val_avg = validate_one_epoch(model, loss_func, data_loader_val,
                                                                            train_device, test_device)
        time_elapsed = timer() - time_start
        val_times.append(time_elapsed)
        val_losses.append(val_loss)
        r2_scores.append(r2_score_val_avg)
        rmse_scores.append(rmse_score_val_avg)

        # Early stopping
        if current_epoch == 1:
            best_val_loss = val_loss
            best_epoch = 1

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_epoch = current_epoch
            no_progress_count = 0
        else:
            no_progress_count += 1

        if no_progress_count == no_progress_max:
            log.log_line(f'\nThe training is stopped in epoch {current_epoch} due to no progress in validation loss:')
            log.log_line(f'\tBest validation loss {best_val_loss} achieved in epoch {best_epoch}')
            break

        log.log_line(f'\nEpoch {current_epoch} summary:')
        log.log_line(f'\tTrain loss: {train_loss}')
        log.log_line(f'\tValidation loss: {val_loss}')
        log.log_line(f'\tValidation R^2 score: {r2_score_val_avg}')
        log.log_line(f'\tValidation RMSE score: {rmse_score_val_avg}')

    # Retraining model on train+val dataset
    log.log_line("\nRetraining model on train+val dataset...")
    retrain_times = []
    for current_epoch in range(1, best_epoch + 2):
        time_start = timer()
        train_one_epoch(data_loader_trainval, loss_func, model, optimizer, train_device)
        time_elapsed = timer() - time_start
        retrain_times.append(time_elapsed)
        log.log_line(f"\tFinished epoch {current_epoch} of {best_epoch + 1}")

    # Serialize model for later usage
    torch.save([model, train_losses, val_losses, r2_scores, rmse_scores, train_times, val_times, retrain_times],
               model_path)
    return model_path, log


# Test the model
def test(predict_device, test_device, model_path: str, log: FileLogger):
    testset = DatasetClass(csv_file_x, csv_file_y, root_dir, "test")
    data_loader_test = DataLoader(testset, batch_size=1, shuffle=True, collate_fn=collate(predict_device))

    # Load the model
    data = torch.load(model_path)
    model = data[0]
    model.to(predict_device)
    train_losses = data[1]
    val_losses = data[2]
    r2_scores_val = data[3]
    rmse_scores_val = data[4]
    # Prepare the metadata for graphs
    best_val_loss = np.argmin(val_losses)
    highest_val_loss = np.maximum(np.max(val_losses), np.max(train_losses))
    # Plot graphs
    fig, (top_ax, bot_ax) = plt.subplots(2)
    fig.suptitle("Training progress")
    fig.set_size_inches(w=len(train_losses) * 0.4, h=15)

    top_ax.set_ylabel("Loss value")
    top_ax.plot(range(len(train_losses)), train_losses, color="blue", linestyle="solid", label="train loss")
    top_ax.plot(range(len(val_losses)), val_losses, color="red", linestyle="solid", label="val loss")
    top_ax.plot([best_val_loss, best_val_loss], [0, highest_val_loss], color="green", linestyle="solid",
                label="best epoch")

    bot_ax.set_ylabel("Score value")
    bot_ax.plot(range(len(r2_scores_val)), r2_scores_val, color="magenta", linestyle="solid", label="val R^2 score")
    bot_ax.plot(range(len(rmse_scores_val)), rmse_scores_val, color="orange", linestyle="solid", label="val RMSE score")
    bot_ax.legend()

    for ax in fig.get_axes():
        ax.set_xticks(range(len(train_losses)))
        ax.set_xticklabels(range(1, len(train_losses) + 1))
        ax.set_xlabel("Epoch #")
        ax.legend()

    plt.savefig(model_path + '.png')

    # Prepare for predicting
    model.eval()
    y_pred = np.empty((0, 31))
    y_true = np.empty((0, 31))

    # Predict
    log.log_line("\nPredicting...\n")
    pred_data_name = model_path + '.predicted'
    true_data_name = model_path + '.true'
    # Check if there are predicted data for this model, and load it
    pred_exists = os.path.exists(pred_data_name)
    true_exists = os.path.exists(true_data_name)
    if pred_exists and true_exists:
        y_pred = np.load(pred_data_name)
        y_true = np.load(true_data_name)
    # Otherwise, predict the values and save to file
    else:
        with torch.no_grad():
            for i, (graph, true_y) in enumerate(data_loader_test):
                pred_y = model(graph.to(predict_device))
                pred_y = np.array(pred_y.to(test_device))
                y_pred = np.vstack((y_pred, pred_y))
                y_true = np.vstack((y_true, true_y.to(test_device)))
            # Save the predicted data
            np.save(pred_data_name, y_pred)
            np.save(true_data_name, y_true)

    # Evaluate
    log.log_line("\nEvaluating...")
    r2_score_test_avg, rmse_score_test_avg = calculate_r2_and_rmse_scores(y_pred, y_true)
    log.log_line(f'\nAverage R2 score: {r2_score_test_avg:.4f}')
    log.log_line(f'Average RMSE score: {rmse_score_test_avg:.4f}\n')

    # More details
    train_times = data[5]
    val_times = data[6]
    retrain_times = data[7]

    log.log_bar()
    log.log_line("Average data")
    log.log_bar()
    log.log_line(f"Training time: {np.average(train_times):.2f}s")
    log.log_line(f"Validating time: {np.average(val_times):.2f}s")
    log.log_line(f"Retraining time: {np.average(retrain_times):.2f}s")

    log.log_bar()
    log.log_line("Total data")
    log.log_bar()
    log.log_line(f"Training time: {np.sum(train_times):.2f}s")
    log.log_line(f"Validating time: {np.sum(val_times):.2f}s")
    log.log_line(f"Retraining time: {np.sum(retrain_times):.2f}s")
