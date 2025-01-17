import argparse
import logging
import os
import random

import numpy as np
import pandas as pd
import torch
from tqdm import tqdm

from DataLoaders.Dataset_Picker import Create_Dataset
from DataLoaders.time_series_dataloader import Create_Dataloader
from Models.Feature_Selector_LightGBM import Feature_Selector_LGBM
from Models.Feature_Selector_XGB import Feature_Selector_XGB
from Models.LightGBM_Pipeline import Baseline_LightGBM_Model
from Models.XGBoost_Pipeline import Baseline_XgBoost_Model
from Models.Cross_Corr_LightGBM import Cross_Corr_LightGBM
from Models.Cross_Corr_XGB import Cross_Corr_XGB
from Models.Mutual_Inf_LightGBM import Mutual_Inf_LightGBM
from Models.Mutual_Inf_XGB import Mutual_Inf_XGB
from Models.RFE_LightGBM import RFE_LightGBM
from Models.RFE_XGB import RFE_XGB



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

parser = argparse.ArgumentParser()
parser.add_argument("--dataset_name", type=str, default="statlog_aca", help="Dataset name")
parser.add_argument("--type", type=str, default="Classification", help="Type of dataset")

if __name__ == '__main__':
    dataset_name = parser.parse_args().dataset_name
    data_type = parser.parse_args().type

    directory_name = f"{data_type}/{dataset_name}"

    if not os.path.exists("Results/" + directory_name):
        os.makedirs("Results/" + directory_name)
        os.makedirs("Results/" + directory_name + "/fs_model")
        os.makedirs("Results/" + directory_name + "/baseline_model")
        os.makedirs("Results/" + directory_name + "/greedy_model")
        print("Directory created successfully")
    else:
        print("Directory already exists")

    logging.basicConfig(filename='console_lgbm.log', level=logging.DEBUG)
    logging.info('Feature Selector LGBM Log')

    if data_type == "Classification":
        dataset = Create_Dataset(dataset_name,
                                 val_ratio=0.2,
                                 mask_ratio=0.2,
                                 test_ratio=0.1)

        dataset = Create_Dataloader(dataset)
        for data in tqdm(dataset):
            X_train, y_train, X_val, y_val, X_val_mask, y_val_mask, X_test, y_test = data
            network = Feature_Selector_LGBM(params={"boosting_type": "goss", "importance_type": "gain",
                                                    "verbosity": -1},
                                            param_grid={
                                                'boosting_type': ['goss'],
                                                'num_leaves': [20, 50, 100],
                                                'learning_rate': [0.01, 0.1, 0.5],
                                                'n_estimators': [20, 50, 100],
                                                'subsample': [0.6, 0.8, 1.0],
                                                'colsample_bytree': [0.6, 0.8, 1.0],
                                                # 'reg_alpha': [0.0, 0.1, 0.5],
                                                # 'reg_lambda': [0.0, 0.1, 0.5],
                                                'min_child_samples': [5, 10],
                                            },
                                            X_train=X_train, X_val=X_val,
                                            X_val_mask=X_val_mask, X_test=X_test, y_train=y_train,
                                            y_val=y_val, y_val_mask=y_val_mask, y_test=y_test,
                                            data_type="Classification", dir_name=directory_name)

            network.fit_network()
            test_loss = network.Test_Network()
            test_fs_lgbm_model_loss = test_loss

            network = Feature_Selector_XGB(params={"boosting_type": "gbdt", "importance_type": "gain",
                                                   "verbosity": 0},
                                           param_grid={
                                               'boosting_type': ['gbdt'],
                                               'num_leaves': [20, 50, 100],
                                               'learning_rate': [0.01, 0.1, 0.5],
                                               'n_estimators': [20, 50, 100],
                                               'subsample': [0.6, 0.8, 1.0],
                                               'colsample_bytree': [0.6, 0.8, 1.0],
                                               # 'reg_alpha': [0.0, 0.1, 0.5],
                                               # 'reg_lambda': [0.0, 0.1, 0.5],
                                               'min_child_samples': [5, 10],
                                           },
                                           X_train=X_train, X_val=X_val,
                                           X_val_mask=X_val_mask, X_test=X_test, y_train=y_train,
                                           y_val=y_val, y_val_mask=y_val_mask, y_test=y_test,
                                           data_type="Classification", dir_name=directory_name)

            network.fit_network()
            test_loss = network.Test_Network()
            test_fs_xgb_model_loss = test_loss

            # Baseline LGBM Model
            X_val = pd.concat([X_val, X_val_mask], axis=0)
            y_val = np.concatenate([y_val, y_val_mask], axis=0)
            baseline_network_lgbm = Baseline_LightGBM_Model(params={"boosting_type": "gbdt", "importance_type": "gain",
                                                                    "verbosity": -1},
                                                            param_grid={
                                                                'boosting_type': ['gbdt'],
                                                                'num_leaves': [5, 10],
                                                                'learning_rate': [0.01, 0.1, 0.5],
                                                                'n_estimators': [5, 10],
                                                                'subsample': [0.6, 0.8, 1.0],
                                                                'colsample_bytree': [0.6, 0.8, 1.0],
                                                                # 'reg_alpha': [0.0, 0.1, 0.5],
                                                                # 'reg_lambda': [0.0, 0.1, 0.5],
                                                                'min_child_samples': [5, 10],
                                                            },
                                                            X_train=X_train, X_val=X_val, X_test=X_test,
                                                            y_train=y_train, y_val=y_val, y_test=y_test,
                                                            data_type="Classification", dir_name=directory_name)

            baseline_network_lgbm.Train_with_RandomSearch()
            best_params_xgboost = baseline_network_lgbm.best_params
            best_params_xgboost = {key: [best_params_xgboost[key]] for key in best_params_xgboost}
            test_lgbm_baseline_loss = baseline_network_lgbm.Test_Network()
            if X_train.shape[1] == 451:
                X_train.drop(columns=["y"], inplace=True)

            # Baseline XGB Model
            baseline_network_xgboost = Baseline_XgBoost_Model(params={"boosting_type": "gbdt", "importance_type": "gain",
                                                                        "verbosity": 0},
                                                                param_grid={
                                                                'boosting_type': ['gbdt'],
                                                                'num_leaves': [10, 20],
                                                                'learning_rate': [0.01, 0.1, 0.5],
                                                                'n_estimators': [10, 20],
                                                                'subsample': [0.6, 0.8, 1.0],
                                                                'colsample_bytree': [0.6, 0.8, 1.0],
                                                                # 'reg_alpha': [0.0, 0.1, 0.5],
                                                                # 'reg_lambda': [0.0, 0.1, 0.5],
                                                                'min_child_samples': [5, 10],
                                                                },
                                                                X_train=X_train, X_val=X_val, X_test=X_test,
                                                                y_train=y_train, y_val=y_val, y_test=y_test,
                                                                data_type="Classification", dir_name=directory_name)

            baseline_network_xgboost.Train_with_RandomSearch()
            test_xgboost_baseline_loss = baseline_network_xgboost.Test_Network()
            if X_train.shape[1] == 451:
                X_train.drop(columns=["y"], inplace=True)

            rfe_lgbm = RFE_LightGBM(params={"boosting_type": "gbdt", "importance_type": "gain",
                                            "verbosity": -1},
                                    param_grid={
                                        'boosting_type': ['gbdt'],
                                        'num_leaves': [10, 20],
                                        'learning_rate': [0.01, 0.1, 0.5],
                                        'n_estimators': [10, 20],
                                        'subsample': [0.6, 0.8, 1.0],
                                        'colsample_bytree': [0.6, 0.8, 1.0],
                                        # 'reg_alpha': [0.0, 0.1, 0.5],
                                        # 'reg_lambda': [0.0, 0.1, 0.5],
                                        'min_child_samples': [5, 10],
                                    },
                                    X_train=X_train, X_val=X_val, X_test=X_test,
                                    y_train=y_train, y_val=y_val, y_test=y_test,
                                    data_type="Classification", dir_name=directory_name)

            rfe_lgbm.Train_with_RandomSearch()
            test_lgbm_rfe_loss = rfe_lgbm.Test_Network()
            if X_train.shape[1] == 451:
                X_train.drop(columns=["y"], inplace=True)

            rfe_xgb = RFE_XGB(params={"boosting_type": "gbdt", "importance_type": "gain",
                                      "verbosity": 0},
                              param_grid={
                                  'boosting_type': ['gbdt'],
                                  'num_leaves': [10, 20],
                                  'learning_rate': [0.01, 0.1, 0.5],
                                  'n_estimators': [5, 10, 20],
                                  'subsample': [0.6, 0.8, 1.0],
                                  'colsample_bytree': [0.6, 0.8, 1.0],
                                  # 'reg_alpha': [0.0, 0.1, 0.5],
                                  # 'reg_lambda': [0.0, 0.1, 0.5],
                                  'min_child_samples': [5, 10],
                              },
                              X_train=X_train, X_val=X_val, X_test=X_test,
                              y_train=y_train, y_val=y_val, y_test=y_test,
                              data_type="Classification", dir_name=directory_name)

            rfe_xgb.Train_with_RandomSearch()
            test_xgboost_rfe_loss = rfe_xgb.Test_Network()
            if X_train.shape[1] == 451:
                X_train.drop(columns=["y"], inplace=True)


            cross_corr_lgbm = Cross_Corr_LightGBM(params={"boosting_type": "gbdt", "importance_type": "gain",
                                                          "verbosity": -1},
                                                  param_grid={
                                                      'boosting_type': ['gbdt'],
                                                      'num_leaves': [10, 20],
                                                      'learning_rate': [0.01, 0.1, 0.5],
                                                      'n_estimators': [10, 20],
                                                      'subsample': [0.6, 0.8, 1.0],
                                                      'colsample_bytree': [0.6, 0.8, 1.0],
                                                      # 'reg_alpha': [0.0, 0.1, 0.5],
                                                      # 'reg_lambda': [0.0, 0.1, 0.5],
                                                      'min_child_samples': [5, 10],
                                                  },
                                                  X_train=X_train, X_val=X_val, X_test=X_test,
                                                  y_train=y_train, y_val=y_val, y_test=y_test,
                                                  data_type="Classification", dir_name=directory_name)

            cross_corr_lgbm.Train_with_RandomSearch()
            test_lgbm_cross_corr_loss = cross_corr_lgbm.Test_Network()
            if X_train.shape[1] == 451:
                X_train.drop(columns=["y"], inplace=True)

            cross_corr_xgb = Cross_Corr_XGB(
                params={"boosting_type": "gbdt", "importance_type": "gain",
                        "verbosity": 0},
                param_grid={
                    'boosting_type': ['gbdt'],
                    'num_leaves': [10, 20],
                    'learning_rate': [0.01, 0.1, 0.5],
                    'n_estimators': [5, 10, 20],
                    'subsample': [0.6, 0.8, 1.0],
                    'colsample_bytree': [0.6, 0.8, 1.0],
                    # 'reg_alpha': [0.0, 0.1, 0.5],
                    # 'reg_lambda': [0.0, 0.1, 0.5],
                    'min_child_samples': [5, 10],
                },
                X_train=X_train, X_val=X_val, X_test=X_test,
                y_train=y_train, y_val=y_val, y_test=y_test,
                data_type="Classification", dir_name=directory_name)

            cross_corr_xgb.Train_with_RandomSearch()
            test_xgboost_cross_corr_loss = cross_corr_xgb.Test_Network()
            if X_train.shape[1] == 451:
                X_train.drop(columns=["y"], inplace=True)

            mutual_inf_lgbm = Mutual_Inf_LightGBM(params={"boosting_type": "gbdt", "importance_type": "gain",
                                                          "verbosity": -1},
                                                  param_grid={
                                                      'boosting_type': ['gbdt'],
                                                      'num_leaves': [10, 20],
                                                      'learning_rate': [0.01, 0.1, 0.5],
                                                      'n_estimators': [10, 20],
                                                      'subsample': [0.6, 0.8, 1.0],
                                                      'colsample_bytree': [0.6, 0.8, 1.0],
                                                      # 'reg_alpha': [0.0, 0.1, 0.5],
                                                      # 'reg_lambda': [0.0, 0.1, 0.5],
                                                      'min_child_samples': [5, 10],
                                                  },
                                                  X_train=X_train, X_val=X_val, X_test=X_test,
                                                  y_train=y_train, y_val=y_val, y_test=y_test,
                                                  data_type="Classification", dir_name=directory_name)

            mutual_inf_lgbm.Train_with_RandomSearch()
            test_lgbm_mutual_inf_loss = mutual_inf_lgbm.Test_Network()
            if X_train.shape[1] == 451:
                X_train.drop(columns=["y"], inplace=True)

            mutual_inf_xgb = Mutual_Inf_XGB(params={"boosting_type": "gbdt", "importance_type": "gain",
                                                    "verbosity": 0},
                                            param_grid={
                                                'boosting_type': ['gbdt'],
                                                'num_leaves': [10, 20],
                                                'learning_rate': [0.01, 0.1, 0.5],
                                                'n_estimators': [5, 10, 20],
                                                'subsample': [0.6, 0.8, 1.0],
                                                'colsample_bytree': [0.6, 0.8, 1.0],
                                                # 'reg_alpha': [0.0, 0.1, 0.5],
                                                # 'reg_lambda': [0.0, 0.1, 0.5],
                                                'min_child_samples': [5, 10],
                                            },
                                            X_train=X_train, X_val=X_val, X_test=X_test,
                                            y_train=y_train, y_val=y_val, y_test=y_test,
                                            data_type="Classification", dir_name=directory_name)

            mutual_inf_xgb.Train_with_RandomSearch()
            test_xgboost_mutual_inf_loss = mutual_inf_xgb.Test_Network()
            if X_train.shape[1] == 451:
                X_train.drop(columns=["y"], inplace=True)


            print("------------------------------------------------------------------")
            print("Test Loss for Feature Selector LGBM: ", test_fs_lgbm_model_loss)
            print("Test Loss for Feature Selector XGBoost: ", test_fs_xgb_model_loss)
            print("Test Loss for Baseline LGBM: ", test_lgbm_baseline_loss)
            print("Test Loss for Baseline XGBoost: ", test_xgboost_baseline_loss)
            print("Test Loss for Cross Corr LGBM: ", test_lgbm_cross_corr_loss)
            print("Test Loss for Mutual Inf LGBM: ", test_lgbm_mutual_inf_loss)
            print("Test Loss for RFE LGBM: ", test_lgbm_rfe_loss)
            print("Test Loss for Cross Corr XGBoost: ", test_xgboost_cross_corr_loss)
            print("Test Loss for Mutual Inf XGBoost: ", test_xgboost_mutual_inf_loss)
            print("Test Loss for RFE XGBoost: ", test_xgboost_rfe_loss)
            print("------------------------------------------------------------------")

            np.save(f"Results/Classification/{dataset_name}/test_fs_lgbm_model_loss.npy",
                    np.asarray(test_fs_lgbm_model_loss))
            np.save(f"Results/Classification/{dataset_name}/test_fs_xgb_model_loss.npy",
                    np.asarray(test_fs_xgb_model_loss))
            np.save(f"Results/Classification/{dataset_name}/test_lgbm_baseline_loss.npy",
                    np.asarray(test_lgbm_baseline_loss))
            np.save(f"Results/Classification/{dataset_name}/test_xgboost_baseline_loss.npy",
                    np.asarray(test_xgboost_baseline_loss))
            np.save(f"Results/Classification/{dataset_name}/test_lgbm_cross_corr_loss.npy",
                    np.asarray(test_lgbm_cross_corr_loss))
            np.save(f"Results/Classification/{dataset_name}/test_lgbm_mutual_inf_loss.npy",
                    np.asarray(test_lgbm_mutual_inf_loss))
            np.save(f"Results/Classification/{dataset_name}/test_lgbm_rfe_loss.npy",
                    np.asarray(test_lgbm_rfe_loss))
            np.save(f"Results/Classification/{dataset_name}/test_xgboost_cross_corr_loss.npy",
                    np.asarray(test_xgboost_cross_corr_loss))




    else:
        dataset = Create_Dataset(dataset_name)
        dataset = Create_Dataloader(dataset)
        test_fs_lgbm_model_loss = []
        test_fs_xgb_model_loss = []
        test_lgbm_baseline_loss = []
        test_xgboost_baseline_loss = []
        test_lgbm_cross_corr_loss = []
        test_xgboost_cross_corr_loss = []
        test_lgbm_mutual_inf_loss = []
        test_xgboost_mutual_inf_loss = []
        test_lgbm_rfe_loss = []
        test_xgboost_rfe_loss = []
        count = 0
        for data in tqdm(dataset):
            count += 1
            X_train, y_train, X_val, y_val, X_val_mask, y_val_mask, X_test, y_test = data
            network = Feature_Selector_LGBM(params={"boosting_type": "gbdt", "importance_type": "gain",
                                                    "verbosity": -1},
                                            param_grid={
                                                'boosting_type': ['gbdt'],
                                                'num_leaves': [20, 50, 100],
                                                'learning_rate': [0.01, 0.1, 0.5],
                                                'n_estimators': [20, 50, 100],
                                                'subsample': [0.6, 0.8, 1.0],
                                                'colsample_bytree': [0.6, 0.8, 1.0],
                                                # 'reg_alpha': [0.0, 0.1, 0.5],
                                                # 'reg_lambda': [0.0, 0.1, 0.5],
                                                'min_child_samples': [5, 10],
                                            },
                                            X_train=X_train, X_val=X_val,
                                            X_val_mask=X_val_mask, X_test=X_test, y_train=y_train,
                                            y_val=y_val, y_val_mask=y_val_mask, y_test=y_test,
                                            data_type="Regression", dir_name=directory_name)

            network.fit_network()
            test_loss = network.Test_Network()
            test_fs_lgbm_model_loss.append(test_loss)

            network = Feature_Selector_XGB(params={"boosting_type": "gbdt", "importance_type": "gain",
                                                   "verbosity": 0},
                                           param_grid={
                                               'boosting_type': ['gbdt'],
                                               'num_leaves': [20, 50, 100],
                                               'learning_rate': [0.01, 0.1, 0.5],
                                               'n_estimators': [20, 50, 100],
                                               'subsample': [0.6, 0.8, 1.0],
                                               'colsample_bytree': [0.6, 0.8, 1.0],
                                               # 'reg_alpha': [0.0, 0.1, 0.5],
                                               # 'reg_lambda': [0.0, 0.1, 0.5],
                                               'min_child_samples': [5, 10],
                                           },
                                           X_train=X_train, X_val=X_val,
                                           X_val_mask=X_val_mask, X_test=X_test, y_train=y_train,
                                           y_val=y_val, y_val_mask=y_val_mask, y_test=y_test,
                                           data_type="Regression", dir_name=directory_name)

            network.fit_network()
            test_loss = network.Test_Network()
            test_fs_xgb_model_loss.append(test_loss)

            # Baseline LGBM Model
            X_val = pd.concat([X_val, X_val_mask], axis=0)
            y_val = np.concatenate([y_val, y_val_mask], axis=0)
            baseline_network_lgbm = Baseline_LightGBM_Model(params={"boosting_type": "gbdt", "importance_type": "gain",
                                                                    "verbosity": -1},
                                                            param_grid={
                                                                'boosting_type': ['gbdt'],
                                                                'num_leaves': [5, 10],
                                                                'learning_rate': [0.01, 0.1, 0.5],
                                                                'n_estimators': [5, 10],
                                                                'subsample': [0.6, 0.8, 1.0],
                                                                'colsample_bytree': [0.6, 0.8, 1.0],
                                                                # 'reg_alpha': [0.0, 0.1, 0.5],
                                                                # 'reg_lambda': [0.0, 0.1, 0.5],
                                                                'min_child_samples': [5, 10],
                                                            },
                                                            X_train=X_train, X_val=X_val, X_test=X_test,
                                                            y_train=y_train, y_val=y_val, y_test=y_test,
                                                            data_type="Regression", dir_name=directory_name)

            baseline_network_lgbm.Train_with_RandomSearch()
            best_params_xgboost = baseline_network_lgbm.best_params
            best_params_xgboost = {key: [best_params_xgboost[key]] for key in best_params_xgboost}
            test_lgbm_baseline_loss.append(baseline_network_lgbm.Test_Network())
            if X_train.shape[1] == 177:
                X_train.drop(columns=["y"], inplace=True)

            # Baseline XGB Model
            baseline_network_xgboost = Baseline_XgBoost_Model(
                params={"boosting_type": "gbdt", "importance_type": "gain",
                        "verbosity": 0},
                param_grid={
                    'boosting_type': ['gbdt'],
                    'num_leaves': [10, 20],
                    'learning_rate': [0.01, 0.1, 0.5],
                    'n_estimators': [10, 20],
                    'subsample': [0.6, 0.8, 1.0],
                    'colsample_bytree': [0.6, 0.8, 1.0],
                    # 'reg_alpha': [0.0, 0.1, 0.5],
                    # 'reg_lambda': [0.0, 0.1, 0.5],
                    'min_child_samples': [5, 10],
                },
                X_train=X_train, X_val=X_val, X_test=X_test,
                y_train=y_train, y_val=y_val, y_test=y_test,
                data_type="Regression", dir_name=directory_name)

            baseline_network_xgboost.Train_with_RandomSearch()
            test_xgboost_baseline_loss.append(baseline_network_xgboost.Test_Network())
            if X_train.shape[1] == 177:
                X_train.drop(columns=["y"], inplace=True)

            rfe_lgbm = RFE_LightGBM(params={"boosting_type": "gbdt", "importance_type": "gain",
                                            "verbosity": -1},
                                    param_grid={
                                        'boosting_type': ['gbdt'],
                                        'num_leaves': [10, 20],
                                        'learning_rate': [0.01, 0.1, 0.5],
                                        'n_estimators': [10, 20],
                                        'subsample': [0.6, 0.8, 1.0],
                                        'colsample_bytree': [0.6, 0.8, 1.0],
                                        # 'reg_alpha': [0.0, 0.1, 0.5],
                                        # 'reg_lambda': [0.0, 0.1, 0.5],
                                        'min_child_samples': [5, 10],
                                    },
                                    X_train=X_train, X_val=X_val, X_test=X_test,
                                    y_train=y_train, y_val=y_val, y_test=y_test,
                                    data_type="Regression", dir_name=directory_name)

            rfe_lgbm.Train_with_RandomSearch()
            test_lgbm_rfe_loss.append(rfe_lgbm.Test_Network())
            if X_train.shape[1] == 177:
                X_train.drop(columns=["y"], inplace=True)

            rfe_xgb = RFE_XGB(params={"boosting_type": "gbdt", "importance_type": "gain",
                                      "verbosity": 0},
                              param_grid={
                                  'boosting_type': ['gbdt'],
                                  'num_leaves': [10, 20],
                                  'learning_rate': [0.01, 0.1, 0.5],
                                  'n_estimators': [5, 10, 20],
                                  'subsample': [0.6, 0.8, 1.0],
                                  'colsample_bytree': [0.6, 0.8, 1.0],
                                  # 'reg_alpha': [0.0, 0.1, 0.5],
                                  # 'reg_lambda': [0.0, 0.1, 0.5],
                                  'min_child_samples': [5, 10],
                              },
                              X_train=X_train, X_val=X_val, X_test=X_test,
                              y_train=y_train, y_val=y_val, y_test=y_test,
                              data_type="Regression", dir_name=directory_name)

            rfe_xgb.Train_with_RandomSearch()
            test_xgboost_rfe_loss.append(rfe_xgb.Test_Network())
            if X_train.shape[1] == 177:
                X_train.drop(columns=["y"], inplace=True)


            cross_corr_lgbm = Cross_Corr_LightGBM(params={"boosting_type": "gbdt", "importance_type": "gain",
                                                          "verbosity": -1},
                                                  param_grid={
                                                      'boosting_type': ['gbdt'],
                                                      'num_leaves': [10, 20],
                                                      'learning_rate': [0.01, 0.1, 0.5],
                                                      'n_estimators': [10, 20],
                                                      'subsample': [0.6, 0.8, 1.0],
                                                      'colsample_bytree': [0.6, 0.8, 1.0],
                                                      # 'reg_alpha': [0.0, 0.1, 0.5],
                                                      # 'reg_lambda': [0.0, 0.1, 0.5],
                                                      'min_child_samples': [5, 10],
                                                  },
                                                  X_train=X_train, X_val=X_val, X_test=X_test,
                                                  y_train=y_train, y_val=y_val, y_test=y_test,
                                                  data_type="Regression", dir_name=directory_name)

            cross_corr_lgbm.Train_with_RandomSearch()
            test_lgbm_cross_corr_loss.append(cross_corr_lgbm.Test_Network())
            if X_train.shape[1] == 177:
                X_train.drop(columns=["y"], inplace=True)

            cross_corr_xgb = Cross_Corr_XGB(
                params={"boosting_type": "gbdt", "importance_type": "gain",
                        "verbosity": 0},
                param_grid={
                    'boosting_type': ['gbdt'],
                    'num_leaves': [10, 20],
                    'learning_rate': [0.01, 0.1, 0.5],
                    'n_estimators': [5, 10, 20],
                    'subsample': [0.6, 0.8, 1.0],
                    'colsample_bytree': [0.6, 0.8, 1.0],
                    # 'reg_alpha': [0.0, 0.1, 0.5],
                    # 'reg_lambda': [0.0, 0.1, 0.5],
                    'min_child_samples': [5, 10],
                },
                X_train=X_train, X_val=X_val, X_test=X_test,
                y_train=y_train, y_val=y_val, y_test=y_test,
                data_type="Regression", dir_name=directory_name)

            cross_corr_xgb.Train_with_RandomSearch()
            test_xgboost_cross_corr_loss.append(cross_corr_xgb.Test_Network())
            if X_train.shape[1] == 177:
                X_train.drop(columns=["y"], inplace=True)

            mutual_inf_lgbm = Mutual_Inf_LightGBM(params={"boosting_type": "gbdt", "importance_type": "gain",
                                                          "verbosity": -1},
                                                  param_grid={
                                                      'boosting_type': ['gbdt'],
                                                      'num_leaves': [10, 20],
                                                      'learning_rate': [0.01, 0.1, 0.5],
                                                      'n_estimators': [10, 20],
                                                      'subsample': [0.6, 0.8, 1.0],
                                                      'colsample_bytree': [0.6, 0.8, 1.0],
                                                      # 'reg_alpha': [0.0, 0.1, 0.5],
                                                      # 'reg_lambda': [0.0, 0.1, 0.5],
                                                      'min_child_samples': [5, 10],
                                                  },
                                                  X_train=X_train, X_val=X_val, X_test=X_test,
                                                  y_train=y_train, y_val=y_val, y_test=y_test,
                                                  data_type="Regression", dir_name=directory_name)

            mutual_inf_lgbm.Train_with_RandomSearch()
            test_lgbm_mutual_inf_loss.append(mutual_inf_lgbm.Test_Network())
            if X_train.shape[1] == 177:
                X_train.drop(columns=["y"], inplace=True)

            mutual_inf_xgb = Mutual_Inf_XGB(params={"boosting_type": "gbdt", "importance_type": "gain",
                                                    "verbosity": 0},
                                            param_grid={
                                                'boosting_type': ['gbdt'],
                                                'num_leaves': [10, 20],
                                                'learning_rate': [0.01, 0.1, 0.5],
                                                'n_estimators': [5, 10, 20],
                                                'subsample': [0.6, 0.8, 1.0],
                                                'colsample_bytree': [0.6, 0.8, 1.0],
                                                # 'reg_alpha': [0.0, 0.1, 0.5],
                                                # 'reg_lambda': [0.0, 0.1, 0.5],
                                                'min_child_samples': [5, 10],
                                            },
                                            X_train=X_train, X_val=X_val, X_test=X_test,
                                            y_train=y_train, y_val=y_val, y_test=y_test,
                                            data_type="Regression", dir_name=directory_name)

            mutual_inf_xgb.Train_with_RandomSearch()
            test_xgboost_mutual_inf_loss.append(mutual_inf_xgb.Test_Network())
            if X_train.shape[1] == 177:
                X_train.drop(columns=["y"], inplace=True)

            print("------------------------------------------------------------------")
            print("Test Loss for Feature Selector LGBM: ", test_fs_lgbm_model_loss[-1])
            print("Test Loss for Feature Selector XGBoost: ", test_fs_xgb_model_loss[-1])
            print("Test Loss for Baseline LGBM: ", test_lgbm_baseline_loss[-1])
            print("Test Loss for Baseline XGBoost: ", test_xgboost_baseline_loss[-1])
            print("Test Loss for Cross Corr LGBM: ", test_lgbm_cross_corr_loss[-1])
            print("Test Loss for Mutual Inf LGBM: ", test_lgbm_mutual_inf_loss[-1])
            print("Test Loss for RFE LGBM: ", test_lgbm_rfe_loss[-1])
            print("Test Loss for Cross Corr XGBoost: ", test_xgboost_cross_corr_loss[-1])
            print("Test Loss for Mutual Inf XGBoost: ", test_xgboost_mutual_inf_loss[-1])
            print("Test Loss for RFE XGBoost: ", test_xgboost_rfe_loss[-1])
            print("------------------------------------------------------------------")

            np.save(f"Results/Regression/{dataset_name}/test_fs_lgbm_model_loss.npy",
                    np.asarray(test_fs_lgbm_model_loss))
            np.save(f"Results/Regression/{dataset_name}/test_fs_xgb_model_loss.npy",
                    np.asarray(test_fs_xgb_model_loss))
            np.save(f"Results/Regression/{dataset_name}/test_lgbm_baseline_loss.npy",
                    np.asarray(test_lgbm_baseline_loss))
            np.save(f"Results/Regression/{dataset_name}/test_xgboost_baseline_loss.npy",
                    np.asarray(test_xgboost_baseline_loss))
            np.save(f"Results/Regression/{dataset_name}/test_lgbm_cross_corr_loss.npy",
                    np.asarray(test_lgbm_cross_corr_loss))
            np.save(f"Results/Regression/{dataset_name}/test_lgbm_mutual_inf_loss.npy",
                    np.asarray(test_lgbm_mutual_inf_loss))
            np.save(f"Results/Regression/{dataset_name}/test_lgbm_rfe_loss.npy",
                    np.asarray(test_lgbm_rfe_loss))
            np.save(f"Results/Regression/{dataset_name}/test_xgboost_cross_corr_loss.npy",
                    np.asarray(test_xgboost_cross_corr_loss))
            np.save(f"Results/Regression/{dataset_name}/test_xgboost_mutual_inf_loss.npy",
                    np.asarray(test_xgboost_mutual_inf_loss))
            np.save(f"Results/Regression/{dataset_name}/test_xgboost_rfe_loss.npy",
                    np.asarray(test_xgboost_rfe_loss))
