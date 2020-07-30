from typing import Optional, Sequence
import numpy as np


class GraphData:
  """GraphData class

  This data class is almost same as `torch_geometric.data.Data
  <https://pytorch-geometric.readthedocs.io/en/latest/modules/data.html#torch_geometric.data.Data>`_.

  Attributes
  ----------
  node_features: np.ndarray
    Node feature matrix with shape [num_nodes, num_node_features]
  edge_index: np.ndarray, dtype int
    Graph connectivity in COO format with shape [2, num_edges]
  edge_features: np.ndarray, optional (default None)
    Edge feature matrix with shape [num_edges, num_edge_features]
  graph_features: np.ndarray, optional (default None)
    Graph feature vector with shape [num_graph_features,]
  num_nodes: int
    The number of nodes in the graph
  num_node_features: int
    The number of features per node in the graph
  num_edges: int
    The number of edges in the graph
  num_edges_features: int, optional (default None)
    The number of features per edge in the graph

  Examples
  --------
  >>> import numpy as np
  >>> node_features = np.random.rand(5, 10)
  >>> edge_index = np.array([[0, 1, 2, 2, 3], [1, 2, 3, 3, 4]], dtype=np.int)
  >>> Graph(node_features=node_features, edge_index=edge_index)
  """

  def __init__(
      self,
      node_features: np.ndarray,
      edge_index: np.ndarray,
      edge_features: Optional[np.ndarray] = None,
      graph_features: Optional[np.ndarray] = None,
  ):
    """
    Parameters
    ----------
    node_features: np.ndarray
      Node feature matrix with shape [num_nodes, num_node_features]
    edge_index: np.ndarray, dtype int
      Graph connectivity in COO format with shape [2, num_edges]
    edge_features: np.ndarray, optional (default None)
      Edge feature matrix with shape [num_edges, num_edge_features]
    graph_features: np.ndarray, optional (default None)
      Graph feature vector with shape [num_graph_features,]
    """
    # validate params
    if isinstance(node_features, np.ndarray) is False:
      raise ValueError('node_features must be np.ndarray.')

    if isinstance(edge_index, np.ndarray) is False:
      raise ValueError('edge_index must be np.ndarray.')
    elif edge_index.dtype != np.int:
      raise ValueError('edge_index.dtype must be np.int')
    elif edge_index.shape[0] != 2:
      raise ValueError('The shape of edge_index is [2, num_edges].')

    if edge_features is not None:
      if isinstance(edge_features, np.ndarray) is False:
        raise ValueError('edge_features must be np.ndarray or None.')
      elif edge_index.shape[1] != edge_features.shape[0]:
        raise ValueError('The first dimension of edge_features must be the \
                    same as the second dimension of edge_index.')

    if graph_features is not None and isinstance(graph_features,
                                                 np.ndarray) is False:
      raise ValueError('graph_features must be np.ndarray or None.')

    self.node_features = node_features
    self.edge_index = edge_index
    self.edge_features = edge_features
    self.graph_features = graph_features
    self.num_nodes, self.num_node_features = self.node_features.shape
    self.num_edges = edge_index.shape[1]
    if self.node_features is not None:
      self.num_edge_features = self.edge_features.shape[1]

  def to_pyg_graph(self):
    """Convert to PyTorch Geometric graph data instance

    Returns
    -------
    torch_geometric.data.Data
      Graph data for PyTorch Geometric
    """
    try:
      import torch
      from torch_geometric.data import Data
    except ModuleNotFoundError:
      raise ValueError(
          "This function requires PyTorch Geometric to be installed.")

    return Data(
      x=torch.from_numpy(self.node_features),
      edge_index=torch.from_numpy(self.edge_index),
      edge_attr=None if self.edge_features is None \
        else torch.from_numpy(self.edge_features),
    )

  def to_dgl_graph(self):
    """Convert to DGL graph data instance

    Returns
    -------
    dgl.DGLGraph
      Graph data for PyTorch Geometric
    """
    try:
      from dgl import DGLGraph
    except ModuleNotFoundError:
      raise ValueError("This function requires DGL to be installed.")

    g = DGLGraph()
    g.add_nodes(self.num_nodes)
    g.add_edges(self.edge_index[0], self.edge_index[1])
    g.ndata['x'] = torch.from_numpy(self.node_features)

    if self.edge_features is not None:
      g.edata['edge_attr'] = torch.from_numpy(self.edge_features)

    return g


class BatchGraphData(GraphData):
  """Batch GraphData class

  Attributes
  ----------
  graph_index: np.ndarray, dtype int
    This vector indicates which graph the node belongs with shape [num_nodes,]

  Examples
  --------
  >>> import numpy as np
  >>> node_features_list = np.random.rand(2, 5, 10)
  >>> edge_index_list = np.array([
  ...    [[0, 1, 2, 2, 3], [1, 2, 3, 3, 4]],
  ...    [[0, 1, 2, 2, 3], [1, 2, 3, 3, 4]],
  ... ], dtype=np.int)
  >>> graphs = [Graph(node_features, edge_index) for node_features, edge_index
  ...           in zip(node_features_list, edge_index_list)]
  >>> BatchGraphData(graphs=graphs)
  """

  def __init__(self, graphs: Sequence[GraphData]):
    """
    Parameters
    ----------
    graphs: Sequence[GraphData]
      List of GraphData
    """
    # stack features
    batch_node_features = np.vstack([graph.node_features for graph in graphs])

    # before stacking edge_features or graph_features,
    # we should check whether these are None or not
    if graphs[0].edge_features is not None:
      batch_edge_features = np.vstack([graph.edge_features for graph in graphs])
    else:
      batch_edge_features = None

    if graphs[0].graph_features is not None:
      batch_graph_features = np.vstack(
          [graph.graph_features for graph in graphs])
    else:
      batch_graph_features = None

    # create new edge index
    num_nodes_list = [graph.num_nodes for graph in graphs]
    batch_edge_index = np.hstack(
      [graph.edge_index + prev_num_node for prev_num_node, graph \
        in zip([0] + num_nodes_list[:-1], graphs)]
    ).astype(int)

    # graph_index indicates which nodes belong to which graph
    graph_index = []
    for i, num_nodes in enumerate(num_nodes_list):
      graph_index.extend([i] * num_nodes)
    self.graph_index = np.array(graph_index, dtype=int)

    super().__init__(
        node_features=batch_node_features,
        edge_index=batch_edge_index,
        edge_features=batch_edge_features,
        graph_features=batch_graph_features,
    )
