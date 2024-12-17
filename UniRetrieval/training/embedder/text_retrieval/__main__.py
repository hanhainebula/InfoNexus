from transformers import HfArgumentParser

from UniRetrieval.training.embedder.text_retrieval import *

def main():
    parser = HfArgumentParser((
        EncoderOnlyEmbedderModelArguments,
        EncoderOnlyEmbedderDataArguments,
        EncoderOnlyEmbedderTrainingArguments
    ))
    model_args, data_args, training_args = parser.parse_args_into_dataclasses()
    model_args: EncoderOnlyEmbedderModelArguments
    data_args: EncoderOnlyEmbedderDataArguments
    training_args: EncoderOnlyEmbedderTrainingArguments

    runner = EncoderOnlyEmbedderRunner(
        model_args=model_args,
        data_args=data_args,
        training_args=training_args
    )
    runner.run()


if __name__ == "__main__":
    main()