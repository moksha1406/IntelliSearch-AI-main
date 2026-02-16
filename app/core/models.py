import torch
from packaging.version import parse as version_parse
from transformers import (
    BlipProcessor, BlipForConditionalGeneration,
    AutoTokenizer, AutoModelForSeq2SeqLM,
)
from langchain_huggingface import HuggingFaceEmbeddings

from app.config import *
from app.core.device import DEVICE


def load_caption_model():
    caption_proc = BlipProcessor.from_pretrained(CAPTION_MODEL)
    try:
        caption_model = BlipForConditionalGeneration.from_pretrained(
            CAPTION_MODEL,
            torch_dtype=torch.float16 if DEVICE.type=="cuda" else torch.float32,
            use_safetensors=True,
        ).to(DEVICE).eval()
    except (FileNotFoundError, ValueError):
        if version_parse(torch.__version__) < version_parse("2.6"):
            raise RuntimeError("BLIP weights need safetensors or torch ≥2.6.")
        caption_model = BlipForConditionalGeneration.from_pretrained(
            CAPTION_MODEL,
            torch_dtype=torch.float16 if DEVICE.type=="cuda" else torch.float32,
            use_safetensors=False,
        ).to(DEVICE).eval()

    return caption_proc, caption_model


def load_summarizer():
    sum_tok = AutoTokenizer.from_pretrained(SUMMARIZER)
    sum_mod = AutoModelForSeq2SeqLM.from_pretrained(
        SUMMARIZER,
        torch_dtype=torch.float16 if DEVICE.type=="cuda" else torch.float32,
    ).to(DEVICE).eval()

    return sum_tok, sum_mod

def load_embeddings():
    return HuggingFaceEmbeddings(
        model_name=EMBED_MODEL,
        model_kwargs={"device": DEVICE},
    )
