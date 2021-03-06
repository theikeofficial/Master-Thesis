import os
import random
import pickle as pkl
from typing import Union

import numpy as np
import torch
from sklearn import multioutput

from code.preprocessing.os.arguments import cmd_args
from code.preprocessing.cnf.generate_data import generate_edgelist_formats, generate_satzilla_features, \
    generate_dgcnn_formats, generate_dgcnn_pickled_data, generate_cnf_datasets
from code import knn, rf, gcn, gat, dgcnn
from code.common.data import load_data, scale_the_data
from code.common.process_results import save_the_best_model, calculate_r2_and_rmse_metrics, plot_r2_and_rmse_scores, \
    calculate_r2_and_rmse_metrics_nn, plot_r2_and_rmse_scores_nn, plot_losses_nn


# Globals for KNN and RF models
x_train = None
y_train = None
x_val = None
y_val = None
x_train_val = None
y_train_val = None
x_test = None
y_test = None
solver_names = None
r2_scores_test = None
rmse_scores_test = None

# Globals for DGCNN model

# Globals for GCN and GAT models
train_device = torch.device("cuda:0" if cmd_args.mode == "gpu" else "cpu")
test_device = torch.device("cpu")
trainset = None
valset = None
trainvalset = None
testset = None

# Globals for all models
ModelTypes = Union[multioutput.MultiOutputRegressor, gcn.GCN, gat.GAT, dgcnn.DGCNNPredictor]
best_model: ModelTypes


def data_preparation():
    global x_train, y_train, x_val, y_val, x_train_val, y_train_val, x_test, y_test, solver_names, best_model, trainset, valset, trainvalset, testset

    print('Generating edgelist formats...')
    generate_edgelist_formats(os.path.join(cmd_args.cnf_dir, "splits.csv"), cmd_args.cnf_dir)

    if cmd_args.model == "KNN" or cmd_args.model == "RF":
        print('Generating SATzilla2012 features...')
        generate_satzilla_features(os.path.join(cmd_args.cnf_dir, "splits.csv"), "./", cmd_args.cnf_dir)

        x_train, y_train, x_val, y_val, x_train_val, y_train_val, x_test, y_test = load_data(cmd_args.cnf_dir)
        x_train, x_val, x_train_val, x_test = scale_the_data(x_train, x_val, x_train_val, x_test)
        solver_names = y_train.columns
    elif cmd_args.model == "GCN" or cmd_args.model == "GAT":
        print('Generating CNF dataset with Node2Vec features...')
        training_data, testset = \
            generate_cnf_datasets(cmd_args.cnf_dir,
                                  os.path.join(cmd_args.cnf_dir, "splits.csv"),
                                  os.path.join(cmd_args.cnf_dir, "all_data_y.csv"))
        trainset, valset, trainvalset = training_data
    elif cmd_args.model == "DGCNN":
        print('Generating DGCNN formats...')
        generate_dgcnn_formats(os.path.join(cmd_args.cnf_dir, "splits.csv"),
                               os.path.join(cmd_args.cnf_dir, "all_data_y.csv"),
                               cmd_args.cnf_dir,
                               cmd_args.model_output_dir,
                               cmd_args.model)

        random.seed(cmd_args.seed)
        np.random.seed(cmd_args.seed)
        torch.manual_seed(cmd_args.seed)

        # De-pickle metadata about instances
        instance_ids_filename = os.path.join(cmd_args.model_output_dir, cmd_args.model, "instance_ids.pickled")
        with open(instance_ids_filename, "rb") as f:
            instance_ids, splits = pkl.load(f)

        num_class, feat_dim, edge_feat_dim, attr_dim, sortpooling_k = \
            generate_dgcnn_pickled_data(cmd_args.model_output_dir,
                                        cmd_args.cnf_dir,
                                        instance_ids,
                                        splits,
                                        cmd_args.sortpooling_k)
        cmd_args.num_class = num_class
        cmd_args.feat_dim = feat_dim
        cmd_args.edge_feat_dim = edge_feat_dim
        cmd_args.attr_dim = attr_dim
        cmd_args.sortpooling_k = sortpooling_k

        best_model = dgcnn.DGCNNPredictor(cmd_args.cnf_dir,
                                          cmd_args.model_output_dir,
                                          cmd_args.model,
                                          instance_ids,
                                          splits,
                                          cmd_args.latent_dim,
                                          cmd_args.out_dim,
                                          cmd_args.hidden,
                                          cmd_args.num_class,
                                          cmd_args.dropout,
                                          cmd_args.feat_dim,
                                          cmd_args.attr_dim,
                                          cmd_args.edge_feat_dim,
                                          cmd_args.sortpooling_k,
                                          cmd_args.conv1d_activation,
                                          cmd_args.learning_rate,
                                          cmd_args.mode)


def train_model():
    global x_train, y_train, x_val, y_val, x_train_val, y_train_val, best_model, train_device, test_device

    if cmd_args.model == "KNN":
        knn.train(x_train, y_train, x_val, y_val, solver_names, cmd_args.model_dir)
        best_model = knn.retrain_the_best_model(x_train_val, y_train_val, cmd_args.model_dir)
    elif cmd_args.model == "RF":
        rf.train(x_train, y_train, x_val, y_val, solver_names, cmd_args.model_dir)
        best_model = rf.retrain_the_best_model(x_train_val, y_train_val, cmd_args.model_dir)
    elif cmd_args.model == "GCN":
        gcn.train(cmd_args.model_output_dir, cmd_args.model, trainset, valset, trainvalset, train_device, test_device)
    elif cmd_args.model == "GAT":
        gat.train(cmd_args.model_output_dir, cmd_args.model, trainset, valset, trainvalset, train_device, test_device)
    elif cmd_args.model == "DGCNN":
        dgcnn.train(best_model, cmd_args.num_epochs, cmd_args.batch_size, cmd_args.look_behind, cmd_args.print_auc)
        dgcnn.retrain(best_model, cmd_args.batch_size, cmd_args.extract_features, cmd_args.print_auc)
        
    if cmd_args.model == "KNN" or cmd_args.model == "RF":
        save_the_best_model(best_model, cmd_args.model_dir, cmd_args.model)


def evaluate_model():
    global x_test, y_test, best_model, r2_scores_test, rmse_scores_test, train_device, test_device

    if cmd_args.model == "KNN" or cmd_args.model == "RF":
        _, _, r2_scores_test, rmse_scores_test = calculate_r2_and_rmse_metrics(best_model, x_test, y_test)
        np.savetxt(os.path.join(cmd_args.model_output_dir, cmd_args.model, "r2_scores.txt"), r2_scores_test)
        np.savetxt(os.path.join(cmd_args.model_output_dir, cmd_args.model, "rmse_scores.txt"), rmse_scores_test)
    elif cmd_args.model == "GCN":
        gcn.test(cmd_args.model_output_dir, cmd_args.model, testset, train_device, test_device)
    elif cmd_args.model == "GAT":
        gat.test(cmd_args.model_output_dir, cmd_args.model, testset, train_device, test_device)
    elif cmd_args.model == "DGCNN":
        dgcnn.test(best_model, cmd_args.batch_size, cmd_args.extract_features, cmd_args.print_auc)
        

def process_results():
    global r2_scores_test, rmse_scores_test, solver_names, best_model

    if cmd_args.model == "KNN" or cmd_args.model == "RF":
        plot_r2_and_rmse_scores(r2_scores_test, rmse_scores_test, solver_names, cmd_args.model_dir, cmd_args.model)
    elif cmd_args.model == "DGCNN":
        dgcnn_model_dir = os.path.join(cmd_args.model_output_dir, cmd_args.model)
        _, _, r2_scores_test, rmse_scores_test = calculate_r2_and_rmse_metrics_nn(best_model, dgcnn_model_dir,
                                                                                  cmd_args.model)
        plot_r2_and_rmse_scores_nn(r2_scores_test, rmse_scores_test, dgcnn_model_dir, cmd_args.model)
        plot_losses_nn(cmd_args.model_output_dir, cmd_args.model)


def main():
    # Creating the directory for model outputs
    model_dir = os.path.join(cmd_args.model_output_dir, cmd_args.model)
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)
    cmd_args.model_dir = model_dir

    # Train and evaluate chosen model
    data_preparation()
    train_model()
    evaluate_model()
    process_results()


if __name__ == "__main__":
    main()
