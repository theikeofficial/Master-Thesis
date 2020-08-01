import os
import pickle as pkl

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from sklearn import metrics


def save_the_best_model(best_model, model_output_dir, model):
    print(f"Saving the best KNN model to a file")

    model_filepath = os.path.join(model_output_dir, f"best_{model}_model")
    if os.path.exists(model_filepath):
        return

    with open(model_filepath, "wb") as model_file:
        pkl.dump(best_model, model_file)


def calculate_r2_and_rmse_metrics(best_model, x_test, y_test, y_pred=None):
    if x_test is None and y_pred is None:
        raise ValueError("You must pass either x_test or y_pred")
    if x_test is not None and y_pred is not None:
        raise ValueError("You cannot pass both x_test and y_pred")

    print("Evaluating the best model")
    number_of_solvers = y_test.shape[1]
    r2_scores_test = np.empty((number_of_solvers,))
    rmse_scores_test = np.empty((number_of_solvers,))

    y_true = y_test
    if str(type(y_true)).find("DataFrame"):
        y_true = y_true.values

    if y_pred is None:
        y_pred = best_model.predict(x_test)

    for i in range(number_of_solvers):
        r2_scores_test[i] = metrics.r2_score(y_true[:, i:i + 1], y_pred[:, i:i + 1])
        rmse_scores_test[i] = metrics.mean_squared_error(y_true[:, i:i + 1], y_pred[:, i:i + 1], squared=False)

    return r2_scores_test, rmse_scores_test


def calculate_r2_and_rmse_metrics_nn(best_model, model_output_dir, model):
    y_pred = np.loadtxt(os.path.join(model_output_dir, model, "test_ypred.txt"))
    y_true = np.loadtxt(os.path.join(model_output_dir, model, "test_ytrue.txt"))

    return calculate_r2_and_rmse_metrics(best_model, None, y_true, y_pred)


def plot_r2_and_rmse_scores(r2_scores_test, rmse_scores_test, solver_names, model_output_dir, model):
    print("Plotting the data")

    r2_score_test_avg = np.average(r2_scores_test)
    rmse_score_test_avg = np.average(rmse_scores_test)

    print(f"Average R2 score: {r2_score_test_avg}, Average RMSE score: {rmse_score_test_avg}")

    png_file = os.path.join(model_output_dir, f"{model}.png")
    if os.path.exists(png_file):
        return

    plt.figure(figsize=(15, 6))

    plt.subplot(1, 2, 1)
    xticks = range(1, len(r2_scores_test) + 1)
    ymin = np.minimum(int(np.floor(np.min(r2_scores_test))), 0.0)
    yticks = np.linspace(ymin, 1, 10 * (1 - ymin))
    ylabels = np.round(yticks, 1)
    plt.title("R2 scores per solver")
    plt.xticks(ticks=xticks, labels=list(solver_names), rotation=90)
    plt.yticks(ticks=yticks, labels=ylabels)
    plt.ylim((np.min(yticks), np.max(yticks)))
    plt.bar(xticks, r2_scores_test, color="#578FF7")
    plt.plot([xticks[0], xticks[-1]], [r2_score_test_avg, r2_score_test_avg], "r-")

    plt.subplot(1, 2, 2)
    xticks = range(1, len(rmse_scores_test) + 1)
    rmse_score_test_max = np.ceil(np.max(rmse_scores_test))
    yticks = np.linspace(0, rmse_score_test_max, 10)
    ylabels = np.round(np.linspace(0, rmse_score_test_max, 10), 1)
    plt.title("RMSE scores per solver")
    plt.xticks(ticks=xticks, labels=list(solver_names), rotation=90)
    plt.yticks(ticks=yticks, labels=ylabels)
    plt.ylim((np.min(yticks), np.max(yticks)))
    plt.bar(xticks, rmse_scores_test, color="#FA6A68")
    plt.plot([xticks[0], xticks[-1]], [rmse_score_test_avg, rmse_score_test_avg], "b-")

    plt.tight_layout()
    plt.savefig(png_file, dpi=300)
    plt.close()


def plot_r2_and_rmse_scores_nn(r2_scores_test, rmse_scores_test, model_output_dir, model):
    solver_names = ["ebglucose", "ebminisat", "glucose2", "glueminisat", "lingeling", "lrglshr", "minisatpsm",
                    "mphaseSAT64", "precosat", "qutersat", "rcl", "restartsat", "cryptominisat2011", "spear-sw",
                    "spear-hw", "eagleup", "sparrow", "marchrw", "mphaseSATm", "satime11", "tnm", "mxc09", "gnoveltyp2",
                    "sattime", "sattimep", "clasp2", "clasp1", "picosat", "mphaseSAT", "sapperlot", "sol"]

    plot_r2_and_rmse_scores(r2_scores_test, rmse_scores_test, solver_names, model_output_dir, model)


def plot_losses_nn(model_output_dir, model):
    train_losses = pd.read_csv(os.path.join(model_output_dir, model, "Train_losses.csv"))
    val_losses = pd.read_csv(os.path.join(model_output_dir, model, "Validation_losses.csv"))

    fig, (top_ax, bot_ax) = plt.subplots(2)
    fig.suptitle("Training/Validation progress")
    fig.set_size_inches(w=len(train_losses) * 0.5, h=15)

    top_ax.set_ylabel("MSE loss value")
    top_ax.plot(range(len(train_losses["mse"])), train_losses["mse"], color="blue", linestyle="solid", label="Train")
    top_ax.plot(range(len(val_losses["mse"])), val_losses["mse"], color="magenta", linestyle="solid", label="Val")

    bot_ax.set_ylabel("MAE loss value")
    bot_ax.plot(range(len(train_losses["mae"])), train_losses["mae"], color="red", linestyle="solid", label="Train")
    bot_ax.plot(range(len(val_losses["mae"])), val_losses["mae"], color="orange", linestyle="solid", label="Val")

    for ax in fig.get_axes():
        ax.set_xticks(range(len(train_losses)))
        ax.set_xticklabels(range(1, len(train_losses) + 1))
        ax.set_xlabel("Epoch #")
        ax.legend()

    plt.savefig(os.path.join(model_output_dir, model, f"{model}_losses.png"))
    plt.close()