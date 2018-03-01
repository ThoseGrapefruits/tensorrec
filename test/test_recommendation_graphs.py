import numpy as np
import tensorflow as tf
import scipy.sparse as sp
from unittest import TestCase

from tensorrec.recommendation_graphs import (
    project_biases, split_sparse_tensor_indices, bias_prediction_dense, bias_prediction_serial,
    gather_sampled_item_predictions, rank_predictions
)
from tensorrec.session_management import get_session


class RecommendationGraphsTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.session = get_session()

    def test_project_biases(self):
        features = sp.coo_matrix([
            [1.0, 0, 0, 1.0],
            [0, 1.0, 0, 0],
            [0, 0, 1.0, 2.0],
        ], dtype=np.float32)
        n_features = 4

        sparse_tensor_features = tf.SparseTensor(np.mat([features.row, features.col]).transpose(),
                                                 features.data,
                                                 features.shape)
        tf_feature_biases, tf_projected_biases = project_biases(tf_features=sparse_tensor_features,
                                                                n_features=n_features)

        self.session.run(tf.global_variables_initializer())
        assign_op = tf_feature_biases.assign(value=[[-.5], [.5], [0], [2.0]])
        self.session.run(assign_op)

        result = tf_projected_biases.eval(session=self.session)
        expected_result = np.array([1.5, .5, 4.0])
        self.assertTrue((result == expected_result).all())

    def test_split_sparse_tensor_indices(self):
        interactions = sp.coo_matrix([
            [1.0, 0, 0, 1.0],
            [0, 1.0, 0, 0],
            [0, 0, 1.0, 2.0],
        ], dtype=np.float32)
        sparse_tensor_interactions = tf.SparseTensor(np.mat([interactions.row, interactions.col]).transpose(),
                                                     interactions.data,
                                                     interactions.shape)

        x_user, x_item = split_sparse_tensor_indices(tf_sparse_tensor=sparse_tensor_interactions, n_dimensions=2)

        x_user = x_user.eval(session=self.session)
        x_item = x_item.eval(session=self.session)

        expected_user = np.array([0, 0, 1, 2, 2])
        expected_item = np.array([0, 3, 1, 2, 3])

        self.assertTrue((x_user == expected_user).all())
        self.assertTrue((x_item == expected_item).all())

    def test_bias_prediction_dense(self):
        predictions = np.array([
            [1.0, 0, 0, 1.0],
            [0, 1.0, 0, 0],
            [0, 0, 1.0, 2.0],
        ], dtype=np.float32)

        projected_user_biases = np.array([0.0, 1.0, 2.0])
        projected_item_biases = np.array([0.0, -1.0, -2.0, -3.0])

        biased_predictions = bias_prediction_dense(
            tf_prediction=predictions,
            tf_projected_user_biases=projected_user_biases,
            tf_projected_item_biases=projected_item_biases
        ).eval(session=self.session)

        expected_biased_predictions = np.array([
            [1.0, -1.0, -2.0, -2.0],
            [1.0, 1.0, -1.0, -2.0],
            [2.0, 1.0, 1.0, 1.0],
        ], dtype=np.float32)

        self.assertTrue((biased_predictions == expected_biased_predictions).all())

    def test_bias_prediction_serial(self):
        predictions = np.array([1.0, 0, 0, 1.0, 0, 1.0, 0, 0, 0, 0, 1.0, 2.0], dtype=np.float32)

        projected_user_biases = np.array([0.0, 1.0, 2.0])
        projected_item_biases = np.array([0.0, -1.0, -2.0, -3.0])

        x_user = np.array([0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2])
        x_item = np.array([0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3])

        biased_predictions = bias_prediction_serial(
            tf_prediction_serial=predictions,
            tf_projected_user_biases=projected_user_biases,
            tf_projected_item_biases=projected_item_biases,
            tf_x_user=x_user,
            tf_x_item=x_item,
        ).eval(session=self.session)

        expected_biased_predictions = np.array([1.0, -1.0, -2.0, -2.0, 1.0, 1.0, -1.0, -2.0, 2.0, 1.0, 1.0, 1.0],
                                               dtype=np.float32)

        self.assertTrue((biased_predictions == expected_biased_predictions).all())

    def test_gather_sampled_item_predictions(self):
        input_data = np.array([
            [1, 2, 3, 4],
            [5, 6, 7, 8],
            [9, 10, 11, 12]
        ])
        sample_indices = np.array([
            [0, 3],  # Corresponds to [1, 4]
            [5, 6],  # Corresponds to [6, 7]
            [8, 8],  # Corresponds to [9, 9]
        ])
        result = gather_sampled_item_predictions(
            tf_prediction=tf.identity(input_data), tf_sampled_item_indices=tf.identity(sample_indices)
        ).eval(session=self.session)

        expected_result = np.array([
            [1, 4],
            [6, 7],
            [9, 9],
        ])
        self.assertTrue((result == expected_result).all())

    def test_rank_predictions(self):
        predictions = np.array([
            [1.0, 2.0, 3.0, 4.0],
            [4.0, 3.0, 2.0, 1.0],
            [3.0, 4.0, 1.0, 2.0],
        ], dtype=np.float32)

        ranked = rank_predictions(predictions).eval(session=self.session)

        expected_ranks = np.array([
            [4, 3, 2, 1],
            [1, 2, 3, 4],
            [2, 1, 4, 3],
        ], dtype=np.int)
        self.assertTrue((ranked == expected_ranks).all())