from pathlib import Path
import json
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from UniRetrieval.abc.training.reranker import AbsRerankerModelArguments, AbsRerankerDataArguments, AbsRerankerTrainingArguments
from UniRetrieval.abc.arguments import AbsArguments
from typing import Dict, Tuple
import torch
from accelerate import Accelerator
from loguru import logger as loguru_logger
import importlib

@dataclass
class TrainingArguments(AbsRerankerTrainingArguments):
    train_batch_size: int = 512
    item_batch_size: int = 2048 # only used for retriever training
    evaluation_strategy: str = "epoch"  # epoch or step
    eval_interval: int = 1    # interval between evaluations, epochs or steps
    eval_batch_size: int = 256
    cutoffs: list = field(default_factory=lambda : [1, 5, 10])
    metrics: list = field(default_factory=lambda : ["ndcg", "recall"])
    earlystop_strategy: str = "epoch"   # epoch or step
    earlystop_patience: int = 5     # number of epochs or steps
    earlystop_metric: str = "ndcg@5"
    earlystop_metric_mode: str = "max"
    checkpoint_best_ckpt: bool = True   # if true, save best model in earystop callback
    checkpoint_steps: int = 1000    # if none, save model per epoch; else save model by steps
    
    
    
# TODO 检查该类是否冗余
class Statistics(AbsArguments):
    @staticmethod
    def from_dict(d: dict):
        stat = Statistics()
        for k, v in d.items():
            setattr(stat, k.strip(), v)
        return stat

    def add_argument(self, name, value):
        setattr(self, name, value)


@dataclass
class DataAttr4Model(AbsArguments):
    """
    Data attributes for a dataset. Serve for models
    """
    fiid: str
    flabels: List[str]
    features: List[str]
    context_features: List[str]
    item_features: List[str]
    seq_features: List[str]
    num_items: int  # number of candidate items instead of maximum id of items
    stats: Statistics

    # TODO 不确定AbsArguments的方法能不能平替
    @staticmethod
    def from_dict(d: dict):
        if "stats" in d:
            d["stats"] = Statistics.from_dict(d["stats"])
        attr = DataAttr4Model(**d)
        return attr

    def to_dict(self):
        d = self.__dict__
        for k, v in d.items():
            if type(v) == Statistics:
                d[k] = v.__dict__
        return d


# TODO 添加了DataAttr4Model
@dataclass
class ModelArguments(AbsRerankerModelArguments):
    # model_name: str = None
    # embedding_dim: int = 10
    # data_config: Optional[DataAttr4Model] = None
    embedding_dim: int = 10
    mlp_layers: list[int] = field(default_factory=list)
    prediction_layers: list[int] = field(default_factory=list)
    num_neg: int = 50
    activation: str = "relu"
    dropout: float = 0.3
    batch_norm: bool = True
    model_name_or_path: str = ''

# TODO 待检查

REQUIRED_DATA_CONFIG = [
    "name",
    "type",
    "url",
    "labels",
    "stats",
    "item_col",
    "context_features",
    "item_features",
    "train_settings/start_date",
    "train_settings/end_date",
    "test_settings/start_date",
    "test_settings/end_date",
]

DEFAULT_CONFIG = {
    "file_format": "auto",
    "date_format": "%Y-%m-%d",
    "user_sequential_info": None,
    "post_process": None,
    "filter_settings": None,
    "item_info": None,
}

@dataclass
class DataArguments(AbsRerankerDataArguments):
    # Required fields without default values
    name: str=None
    type: str=None
    url: str=None
    labels: List[str]=None
    stats: Dict[str, Any]=None
    item_col: str=None
    context_features: List[str]=None
    item_features: List[str]=None

    # Optional fields with default values
    train_settings: Dict[str, datetime] = field(default=None,metadata={"required_keys": ["start_date", "end_date"]})
    test_settings: Dict[str, datetime] = field(default=None,metadata={"required_keys": ["start_date", "end_date"]})
    file_format: str = "auto"
    date_format: str = "%Y-%m-%d"
    user_sequential_info: Optional[Dict[str, Any]] = None
    post_process: Optional[Dict[str, Any]] = None
    filter_settings: Optional[Dict[str, Any]] = None
    item_info: Optional[Dict[str, Any]] = None
    seq_features: List[str] = field(default_factory=list)


    def __post_init__(self):
        # Validate required keys in dictionaries after initialization
        for attr_name, required_keys in [
            ("train_settings", ["start_date", "end_date"]),
            ("test_settings", ["start_date", "end_date"])
        ]:
            attr_value = getattr(self, attr_name)
            missing_keys = [key for key in required_keys if key not in attr_value]
            if missing_keys:
                raise ValueError(f"Missing required keys in {attr_name}: {missing_keys}")
        
        # Convert string dates to datetime objects using the provided date format
        for settings in [self.train_settings, self.test_settings]:
            for key in ["start_date", "end_date"]:
                if isinstance(settings[key], str):
                    settings[key] = datetime.strptime(settings[key], self.date_format)

        # Remove whitespace from feature names and update seq_features if user_sequential_info is provided
        self.context_features = [feat.strip() for feat in self.context_features]
        self.item_features = [feat.strip() for feat in self.item_features]
        if self.user_sequential_info and 'use_cols' in self.user_sequential_info:
            self.seq_features = [feat.strip() for feat in self.user_sequential_info['use_cols']]

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]):
        """Create a DataArguments instance from a dictionary."""
        # Update nested config with default config
        updated_config = cls._update_nested_config(DEFAULT_CONFIG.copy(), config_dict)
        return cls(**updated_config)

    @staticmethod
    def _update_nested_config(defaults: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively update nested dictionaries with defaults."""
        for key, value in defaults.items():
            if key in updates:
                if isinstance(value, dict) and isinstance(updates[key], dict):
                    defaults[key] = DataArguments._update_nested_config(value, updates[key])
                else:
                    defaults[key] = updates[key]
        return defaults

    @classmethod
    def from_json(cls, json_path: str):
        """Create a DataArguments instance from a JSON file."""
        with open(json_path, 'r') as f:
            config_dict = json.load(f)
        return cls.from_dict(config_dict)

