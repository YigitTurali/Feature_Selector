import lightgbm as lgb
import numpy as np
import torch
import random
import datetime
from sklearn.metrics import log_loss, mean_squared_error
from sklearn.model_selection import RandomizedSearchCV, GridSearchCV
import pandas as pd


def set_random_seeds(seed):
    """Set random seed for reproducibility across different libraries."""
    # Set seed for NumPy
    np.random.seed(seed)

    # Set seed for Python's built-in random module
    random.seed(seed)

    # Set seed for PyTorch
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)  # if using multiple GPUs

    # You can add more libraries or functions here, if needed

    print(f"Seeds have been set to {seed} for all random number generators.")


set_random_seeds(222)


class Cross_Corr_LightGBM:
    """Wrapper for LightGBM model with utility functions."""

    def __init__(self, params, param_grid, X_train, X_val, X_test, y_train, y_val, y_test,
                 data_type, dir_name):
        # Initialization with dataset and parameters
        self.params = params
        self.param_grid = param_grid
        self.X_train = X_train
        self.y_train = y_train
        self.X_val = X_val
        self.y_val = y_val
        self.X_test = X_test
        self.y_test = y_test
        self.data_type = data_type
        self.dir_name = dir_name

        self.X_train_mi = X_train
        self.X_val_mi = X_val
        self.X_test_mi = X_test

        if data_type == "Classification":
            self.base_model = lgb.LGBMClassifier(**self.params)
            self.params["eval_metric"] = ["logloss"]
            self.params["objective"] = ["binary"]
            self.criterion = self.cross_entropy

        else:
            self.base_model = lgb.LGBMRegressor(**self.params)
            self.params["eval_metric"] = ["l2"]
            self.params["objective"] = ["regression"]
            self.criterion = self.mean_squared_error

    def Calc_Cross_Corr(self, threshold, best=False):
        """Calculate the cross correlation between features and target."""
        dataset = self.X_train
        dataset["y"] = self.y_train
        correlations = pd.DataFrame(dataset).corr()['y'].drop('y')
        selected_features = correlations[correlations.abs() > threshold].index.tolist()

        if best:
            self.X_train = self.X_train[selected_features]
            self.X_val = self.X_val[selected_features]
            self.X_test = self.X_test[selected_features]
            print("Selected features for Cross Correlation LGBM: ", selected_features)

        else:
            self.X_train_mi = self.X_train[selected_features]
            self.X_val_mi = self.X_val[selected_features]
            self.X_test_mi = self.X_test[selected_features]

    def Train_with_RandomSearch(self):
        """Train the model using random search for hyperparameter optimization."""
        best_loss = np.inf
        best_threshold = 10000
        for threshold in [0.02, 0.03, 0.04, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35]:
            self.Calc_Cross_Corr(threshold)
            random_search = RandomizedSearchCV(self.base_model, param_distributions=self.param_grid, n_iter=100, cv=5,
                                               verbose=-1, n_jobs=-1)
            callbacks = [lgb.early_stopping(10, verbose=0), lgb.log_evaluation(period=0)]
            random_search.fit(self.X_train_mi, self.y_train, eval_set=(self.X_val_mi, self.y_val),
                              callbacks=callbacks)
            self.best_params = random_search.best_params_
            self.searched_trained_model = random_search.best_estimator_
            loss = random_search.best_score_
            if loss < best_loss:
                best_loss = loss
                best_threshold = threshold

        self.Calc_Cross_Corr(best_threshold, best=True)
        random_search = RandomizedSearchCV(self.base_model, param_distributions=self.param_grid, n_iter=100, cv=5,
                                           verbose=-1, n_jobs=-1)
        callbacks = [lgb.early_stopping(10, verbose=0), lgb.log_evaluation(period=0)]
        random_search.fit(self.X_train, self.y_train, eval_set=(self.X_val, self.y_val),
                          callbacks=callbacks)
        self.best_params = random_search.best_params_
        self.searched_trained_model = random_search.best_estimator_

    def Train_with_GridSearch(self):
        """Train the model using grid search for hyperparameter optimization."""

        best_loss = np.inf
        best_threshold = 10000
        for threshold in [0.02, 0.03, 0.04, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35]:
            self.Calc_Cross_Corr(threshold)
            grid_search = GridSearchCV(self.base_model, param_grid=self.param_grid, cv=5, verbose=-1, n_jobs=-1)
            callbacks = [lgb.early_stopping(10, verbose=0), lgb.log_evaluation(period=0)]
            grid_search.fit(self.X_train_mi, self.y_train, eval_set=(self.X_val_mi, self.y_val),
                            callbacks=callbacks)
            self.best_params = grid_search.best_params_
            self.searched_trained_model = grid_search.best_estimator_
            loss = grid_search.best_score_
            if loss < best_loss:
                best_loss = loss
                best_threshold = threshold

        self.Calc_Cross_Corr(best_threshold, best=True)
        grid_search = GridSearchCV(self.base_model, param_grid=self.param_grid, cv=5, verbose=-1, n_jobs=-1)
        callbacks = [lgb.early_stopping(10, verbose=0), lgb.log_evaluation(period=0)]
        grid_search.fit(self.X_train, self.y_train, eval_set=(self.X_val, self.y_val),
                        callbacks=callbacks)
        self.best_params = grid_search.best_params_
        self.searched_trained_model = grid_search.best_estimator_

    def Test_Network(self):
        """Test the trained model."""
        if self.data_type == "Classification":
            self.y_pred = self.searched_trained_model.predict_proba(self.X_test)
            self.y_hat = self.searched_trained_model.predict(self.X_test)
        else:
            self.y_pred = self.searched_trained_model.predict(self.X_test)
        self.loss = self.criterion(self.y_pred, self.y_test)

        date = str(datetime.datetime.now())
        date = date.replace(" ", "_")
        date = date.replace(":", "_")
        date = date.replace(".", "_")

        np.save(
            f"Results/{self.dir_name}/greedy_model/preds_cross_corr_lgbm_{date}.npy",
            self.y_pred)
        np.save(
            f"Results/{self.dir_name}/greedy_model/targets_{date}.npy",
            self.y_test)
        print(f"Test Loss for Cross Correlation LGBM: {self.loss}")
        return self.loss

    @staticmethod
    def cross_entropy(preds, labels):
        """Compute cross entropy loss."""
        return log_loss(labels, preds)

    @staticmethod
    def mean_squared_error(preds, labels):
        """Compute mean squared error."""
        return mean_squared_error(labels, preds)
