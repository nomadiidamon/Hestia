"""Built-in model records and accelerator-tier catalog entries."""

from ..types import AcceleratorType, ModelSize
from .model_catalog import ModelCatalog, ModelCatalogEntry, ModelRecord


MODELS = {
    'aya-expanse:32b': ModelRecord.from_name('aya-expanse:32b'),
    'bakllava:7b': ModelRecord.from_name('bakllava:7b'),
    'cogito:14b': ModelRecord.from_name('cogito:14b'),
    'cogito:32b': ModelRecord.from_name('cogito:32b'),
    'cogito:70b': ModelRecord.from_name('cogito:70b'),
    'cogito:8b': ModelRecord.from_name('cogito:8b'),
    'command-r-plus:104b': ModelRecord.from_name('command-r-plus:104b'),
    'command-r:35b': ModelRecord.from_name('command-r:35b'),
    'deepseek-r1:1.5b': ModelRecord.from_name('deepseek-r1:1.5b'),
    'deepseek-r1:14b': ModelRecord.from_name('deepseek-r1:14b'),
    'deepseek-r1:32b': ModelRecord.from_name('deepseek-r1:32b'),
    'deepseek-r1:70b': ModelRecord.from_name('deepseek-r1:70b'),
    'deepseek-r1:8b': ModelRecord.from_name('deepseek-r1:8b'),
    'exaone-deep:32b': ModelRecord.from_name('exaone-deep:32b'),
    'exaone-deep:7.8b': ModelRecord.from_name('exaone-deep:7.8b'),
    'firefunction-v2:70b': ModelRecord.from_name('firefunction-v2:70b'),
    'functionary:70b': ModelRecord.from_name('functionary:70b'),
    'functionary:7b': ModelRecord.from_name('functionary:7b'),
    'gemma3:12b': ModelRecord.from_name('gemma3:12b'),
    'gemma3:27b': ModelRecord.from_name('gemma3:27b'),
    'granite3.1-dense:2b': ModelRecord.from_name('granite3.1-dense:2b'),
    'granite3.1-dense:8b': ModelRecord.from_name('granite3.1-dense:8b'),
    'granite3.3:2b': ModelRecord.from_name('granite3.3:2b'),
    'hermes3:70b': ModelRecord.from_name('hermes3:70b'),
    'hermes3:8b': ModelRecord.from_name('hermes3:8b'),
    'llama3.1:8b': ModelRecord.from_name('llama3.1:8b'),
    'llama3.2-vision:11b': ModelRecord.from_name('llama3.2-vision:11b'),
    'llama3.2-vision:3b': ModelRecord.from_name('llama3.2-vision:3b'),
    'llama3.2-vision:90b': ModelRecord.from_name('llama3.2-vision:90b'),
    'llama3.2:1b': ModelRecord.from_name('llama3.2:1b'),
    'llama3.2:3b': ModelRecord.from_name('llama3.2:3b'),
    'llama3.3:70b': ModelRecord.from_name('llama3.3:70b'),
    'llava:13b': ModelRecord.from_name('llava:13b'),
    'llava:34b': ModelRecord.from_name('llava:34b'),
    'llava:7b': ModelRecord.from_name('llava:7b'),
    'minicpm-v:3b': ModelRecord.from_name('minicpm-v:3b'),
    'minicpm-v:8b': ModelRecord.from_name('minicpm-v:8b'),
    'mistral-nemo:12b': ModelRecord.from_name('mistral-nemo:12b'),
    'mistral-small3.1:22b': ModelRecord.from_name('mistral-small3.1:22b'),
    'mistral:7b': ModelRecord.from_name('mistral:7b'),
    'moondream:1.8b': ModelRecord.from_name('moondream:1.8b'),
    'phi4-mini:3.8b': ModelRecord.from_name('phi4-mini:3.8b'),
    'phi4-reasoning:14b': ModelRecord.from_name('phi4-reasoning:14b'),
    'qwen2.5:14b': ModelRecord.from_name('qwen2.5:14b'),
    'qwen2.5:32b': ModelRecord.from_name('qwen2.5:32b'),
    'qwen2.5:72b': ModelRecord.from_name('qwen2.5:72b'),
    'qwen2.5:7b': ModelRecord.from_name('qwen2.5:7b'),
    'qwen2.5vl:14b': ModelRecord.from_name('qwen2.5vl:14b'),
    'qwen2.5vl:32b': ModelRecord.from_name('qwen2.5vl:32b'),
    'qwen2.5vl:72b': ModelRecord.from_name('qwen2.5vl:72b'),
    'qwen2.5vl:7b': ModelRecord.from_name('qwen2.5vl:7b'),
    'qwen3:0.6b': ModelRecord.from_name('qwen3:0.6b'),
    'qwen3:1.7b': ModelRecord.from_name('qwen3:1.7b'),
    'qwen3:14b': ModelRecord.from_name('qwen3:14b'),
    'qwen3:30b-a3b': ModelRecord.from_name('qwen3:30b-a3b'),
    'qwen3:32b': ModelRecord.from_name('qwen3:32b'),
    'qwen3:8b': ModelRecord.from_name('qwen3:8b'),
    'qwq:32b': ModelRecord.from_name('qwq:32b'),
    'smollm2:1.7b': ModelRecord.from_name('smollm2:1.7b'),
    'xlam:1b': ModelRecord.from_name('xlam:1b'),
    'xlam:7b': ModelRecord.from_name('xlam:7b'),
    'xlam:8b': ModelRecord.from_name('xlam:8b'),
}


def _models(*names: str) -> tuple[ModelRecord, ...]:
    return tuple(MODELS[name] for name in names)


MODEL_CATALOG = ModelCatalog([
    ModelCatalogEntry(
        AcceleratorType.NVIDIA_CUDA, ModelSize.TINY,
        {
            'models': _models('qwen3:0.6b', 'llama3.2:1b', 'deepseek-r1:1.5b', 'smollm2:1.7b'),
            'thinking': _models('deepseek-r1:1.5b', 'qwen3:0.6b'),
            'tools': _models('qwen3:0.6b', 'llama3.2:1b', 'smollm2:1.7b'),
            'vision': _models(),
        },
        'q8_0', 4, 8192, 'Fast (tiny model)',
    ),
    ModelCatalogEntry(
        AcceleratorType.NVIDIA_CUDA, ModelSize.SMALL,
        {
            'models': _models('qwen3:1.7b', 'llama3.2:3b', 'phi4-mini:3.8b', 'granite3.3:2b'),
            'thinking': _models('qwen3:1.7b', 'deepseek-r1:1.5b'),
            'tools': _models('qwen3:1.7b', 'llama3.2:3b', 'granite3.1-dense:2b', 'xlam:1b'),
            'vision': _models('llama3.2-vision:3b', 'moondream:1.8b', 'minicpm-v:3b'),
        },
        'q6_k', 4, 16384, 'Fast',
    ),
    ModelCatalogEntry(
        AcceleratorType.NVIDIA_CUDA, ModelSize.MEDIUM,
        {
            'models': _models('qwen3:8b', 'llama3.1:8b', 'mistral:7b', 'mistral-nemo:12b', 'qwen2.5:7b'),
            'thinking': _models('qwen3:8b', 'deepseek-r1:8b', 'cogito:8b', 'exaone-deep:7.8b'),
            'tools': _models('qwen3:8b', 'llama3.1:8b', 'qwen2.5:7b', 'hermes3:8b', 'mistral:7b', 'xlam:8b', 'functionary:7b', 'granite3.1-dense:8b'),
            'vision': _models('llava:7b', 'llava:13b', 'llama3.2-vision:11b', 'qwen2.5vl:7b', 'minicpm-v:8b', 'moondream:1.8b', 'bakllava:7b'),
        },
        'q4_k_m', 2, 32768, 'Fast',
    ),
    ModelCatalogEntry(
        AcceleratorType.NVIDIA_CUDA, ModelSize.LARGE,
        {
            'models': _models('qwen3:14b', 'qwen3:32b', 'qwen2.5:32b', 'deepseek-r1:14b', 'command-r:35b'),
            'thinking': _models('qwen3:14b', 'qwen3:32b', 'deepseek-r1:14b', 'deepseek-r1:32b', 'qwq:32b', 'cogito:14b', 'cogito:32b', 'phi4-reasoning:14b', 'exaone-deep:32b'),
            'tools': _models('qwen3:14b', 'qwen3:32b', 'command-r:35b', 'qwen2.5:32b', 'hermes3:8b', 'aya-expanse:32b', 'functionary:7b', 'xlam:7b'),
            'vision': _models('llava:34b', 'qwen2.5vl:14b', 'qwen2.5vl:32b', 'llama3.2-vision:11b', 'minicpm-v:8b', 'gemma3:27b', 'mistral-small3.1:22b'),
        },
        'q4_k_m', 2, 32768, 'Moderate',
    ),
    ModelCatalogEntry(
        AcceleratorType.NVIDIA_CUDA, ModelSize.XLARGE,
        {
            'models': _models('llama3.3:70b', 'qwen2.5:72b', 'qwen3:30b-a3b', 'deepseek-r1:70b', 'command-r-plus:104b'),
            'thinking': _models('deepseek-r1:70b', 'qwen3:30b-a3b', 'cogito:70b', 'qwq:32b', 'exaone-deep:32b'),
            'tools': _models('llama3.3:70b', 'qwen2.5:72b', 'qwen3:30b-a3b', 'hermes3:70b', 'command-r-plus:104b', 'firefunction-v2:70b', 'functionary:70b'),
            'vision': _models('llava:34b', 'qwen2.5vl:72b', 'llama3.2-vision:90b', 'mistral-small3.1:22b', 'gemma3:27b'),
        },
        'q4_k_m', 4, 131072, 'Fast (large model)',
    ),
    ModelCatalogEntry(
        AcceleratorType.AMD_ROCM, ModelSize.TINY,
        {
            'models': _models('qwen3:0.6b', 'llama3.2:1b', 'deepseek-r1:1.5b'),
            'thinking': _models('deepseek-r1:1.5b', 'qwen3:0.6b'),
            'tools': _models('qwen3:0.6b', 'llama3.2:1b'),
            'vision': _models(),
        },
        'q8_0', 2, 8192, 'Moderate (tiny model)',
    ),
    ModelCatalogEntry(
        AcceleratorType.AMD_ROCM, ModelSize.SMALL,
        {
            'models': _models('qwen3:1.7b', 'llama3.2:3b', 'phi4-mini:3.8b'),
            'thinking': _models('qwen3:1.7b', 'deepseek-r1:1.5b'),
            'tools': _models('qwen3:1.7b', 'llama3.2:3b', 'xlam:1b'),
            'vision': _models('llama3.2-vision:3b', 'moondream:1.8b', 'minicpm-v:3b'),
        },
        'q5_k_m', 2, 16384, 'Moderate',
    ),
    ModelCatalogEntry(
        AcceleratorType.AMD_ROCM, ModelSize.MEDIUM,
        {
            'models': _models('qwen3:8b', 'llama3.1:8b', 'mistral:7b', 'qwen2.5:7b'),
            'thinking': _models('qwen3:8b', 'deepseek-r1:8b', 'cogito:8b'),
            'tools': _models('qwen3:8b', 'llama3.1:8b', 'qwen2.5:7b', 'hermes3:8b', 'mistral:7b', 'granite3.1-dense:8b'),
            'vision': _models('llava:7b', 'llama3.2-vision:11b', 'qwen2.5vl:7b', 'minicpm-v:8b', 'moondream:1.8b'),
        },
        'q4_k_m', 2, 32768, 'Moderate',
    ),
    ModelCatalogEntry(
        AcceleratorType.AMD_ROCM, ModelSize.LARGE,
        {
            'models': _models('qwen3:14b', 'qwen3:32b', 'deepseek-r1:14b', 'command-r:35b'),
            'thinking': _models('qwen3:14b', 'qwen3:32b', 'deepseek-r1:14b', 'deepseek-r1:32b', 'qwq:32b', 'cogito:14b', 'phi4-reasoning:14b'),
            'tools': _models('qwen3:14b', 'qwen3:32b', 'command-r:35b', 'qwen2.5:32b', 'aya-expanse:32b'),
            'vision': _models('qwen2.5vl:14b', 'qwen2.5vl:32b', 'llava:34b', 'gemma3:27b', 'mistral-small3.1:22b'),
        },
        'q3_k_m', 1, 32768, 'Slow',
    ),
    ModelCatalogEntry(
        AcceleratorType.AMD_ROCM, ModelSize.XLARGE,
        {
            'models': _models('llama3.3:70b', 'qwen2.5:72b', 'deepseek-r1:70b'),
            'thinking': _models('deepseek-r1:70b', 'qwen3:30b-a3b', 'cogito:70b'),
            'tools': _models('llama3.3:70b', 'qwen2.5:72b', 'hermes3:70b', 'firefunction-v2:70b'),
            'vision': _models('qwen2.5vl:72b', 'llama3.2-vision:90b', 'llava:34b'),
        },
        'q3_k_m', 2, 65536, 'Moderate (large model)',
    ),
    ModelCatalogEntry(
        AcceleratorType.INTEL_ONEAPI, ModelSize.TINY,
        {
            'models': _models('qwen3:0.6b', 'llama3.2:1b', 'smollm2:1.7b'),
            'thinking': _models('deepseek-r1:1.5b', 'qwen3:0.6b'),
            'tools': _models('qwen3:0.6b', 'llama3.2:1b'),
            'vision': _models(),
        },
        'q8_0', 2, 8192, 'Moderate (tiny model)',
    ),
    ModelCatalogEntry(
        AcceleratorType.INTEL_ONEAPI, ModelSize.SMALL,
        {
            'models': _models('qwen3:1.7b', 'llama3.2:3b', 'granite3.3:2b'),
            'thinking': _models('qwen3:1.7b', 'deepseek-r1:1.5b'),
            'tools': _models('qwen3:1.7b', 'llama3.2:3b', 'granite3.1-dense:2b'),
            'vision': _models('moondream:1.8b', 'minicpm-v:3b'),
        },
        'q5_k_m', 2, 8192, 'Moderate',
    ),
    ModelCatalogEntry(
        AcceleratorType.INTEL_ONEAPI, ModelSize.MEDIUM,
        {
            'models': _models('qwen3:8b', 'llama3.1:8b', 'mistral:7b'),
            'thinking': _models('qwen3:8b', 'deepseek-r1:8b'),
            'tools': _models('qwen3:8b', 'llama3.1:8b', 'mistral:7b', 'granite3.1-dense:8b', 'hermes3:8b'),
            'vision': _models('llava:7b', 'qwen2.5vl:7b', 'minicpm-v:8b', 'moondream:1.8b'),
        },
        'q4_k_m', 1, 16384, 'Slow',
    ),
    ModelCatalogEntry(
        AcceleratorType.INTEL_ONEAPI, ModelSize.LARGE,
        {
            'models': _models('qwen3:14b', 'qwen2.5:14b', 'phi4-reasoning:14b'),
            'thinking': _models('qwen3:14b', 'deepseek-r1:14b', 'phi4-reasoning:14b', 'cogito:14b'),
            'tools': _models('qwen3:14b', 'qwen2.5:14b', 'hermes3:8b'),
            'vision': _models('qwen2.5vl:14b', 'gemma3:12b', 'mistral-small3.1:22b'),
        },
        'q3_k_m', 1, 16384, 'Slow',
    ),
    ModelCatalogEntry(
        AcceleratorType.APPLE_METAL, ModelSize.TINY,
        {
            'models': _models('qwen3:0.6b', 'llama3.2:1b', 'smollm2:1.7b'),
            'thinking': _models('deepseek-r1:1.5b', 'qwen3:0.6b'),
            'tools': _models('qwen3:0.6b', 'llama3.2:1b'),
            'vision': _models(),
        },
        'q8_0', 4, 8192, 'Fast (tiny model)',
    ),
    ModelCatalogEntry(
        AcceleratorType.APPLE_METAL, ModelSize.SMALL,
        {
            'models': _models('qwen3:1.7b', 'llama3.2:3b', 'phi4-mini:3.8b'),
            'thinking': _models('qwen3:1.7b', 'deepseek-r1:1.5b'),
            'tools': _models('qwen3:1.7b', 'llama3.2:3b', 'granite3.1-dense:2b'),
            'vision': _models('llama3.2-vision:3b', 'moondream:1.8b', 'minicpm-v:3b'),
        },
        'q6_k', 4, 16384, 'Fast',
    ),
    ModelCatalogEntry(
        AcceleratorType.APPLE_METAL, ModelSize.MEDIUM,
        {
            'models': _models('qwen3:8b', 'llama3.1:8b', 'mistral:7b', 'mistral-nemo:12b'),
            'thinking': _models('qwen3:8b', 'deepseek-r1:8b', 'cogito:8b', 'exaone-deep:7.8b'),
            'tools': _models('qwen3:8b', 'llama3.1:8b', 'mistral:7b', 'qwen2.5:7b', 'hermes3:8b', 'granite3.1-dense:8b'),
            'vision': _models('llava:7b', 'llama3.2-vision:11b', 'qwen2.5vl:7b', 'minicpm-v:8b', 'gemma3:12b', 'moondream:1.8b'),
        },
        'q4_k_m', 2, 32768, 'Fast',
    ),
    ModelCatalogEntry(
        AcceleratorType.APPLE_METAL, ModelSize.LARGE,
        {
            'models': _models('qwen3:14b', 'qwen3:32b', 'deepseek-r1:14b', 'command-r:35b'),
            'thinking': _models('qwen3:14b', 'qwen3:32b', 'deepseek-r1:14b', 'deepseek-r1:32b', 'qwq:32b', 'cogito:14b', 'phi4-reasoning:14b', 'exaone-deep:32b'),
            'tools': _models('qwen3:14b', 'qwen3:32b', 'command-r:35b', 'qwen2.5:32b', 'aya-expanse:32b', 'hermes3:8b'),
            'vision': _models('llava:34b', 'qwen2.5vl:14b', 'qwen2.5vl:32b', 'llama3.2-vision:11b', 'gemma3:27b', 'mistral-small3.1:22b'),
        },
        'q4_k_m', 2, 65536, 'Fast (Apple Silicon advantage)',
    ),
    ModelCatalogEntry(
        AcceleratorType.APPLE_METAL, ModelSize.XLARGE,
        {
            'models': _models('llama3.3:70b', 'qwen2.5:72b', 'qwen3:30b-a3b', 'deepseek-r1:70b'),
            'thinking': _models('deepseek-r1:70b', 'qwen3:30b-a3b', 'cogito:70b', 'qwq:32b', 'exaone-deep:32b'),
            'tools': _models('llama3.3:70b', 'qwen2.5:72b', 'qwen3:30b-a3b', 'hermes3:70b', 'command-r-plus:104b', 'firefunction-v2:70b'),
            'vision': _models('llava:34b', 'qwen2.5vl:72b', 'llama3.2-vision:90b', 'gemma3:27b', 'mistral-small3.1:22b'),
        },
        'q4_k_m', 4, 131072, 'Fast (Apple Silicon advantage)',
    ),
    ModelCatalogEntry(
        AcceleratorType.NONE, ModelSize.TINY,
        {
            'models': _models('qwen3:0.6b', 'llama3.2:1b', 'smollm2:1.7b'),
            'thinking': _models('deepseek-r1:1.5b', 'qwen3:0.6b'),
            'tools': _models('qwen3:0.6b', 'llama3.2:1b'),
            'vision': _models('moondream:1.8b'),
        },
        'q8_0', 1, 4096, 'Slow (CPU only)',
    ),
    ModelCatalogEntry(
        AcceleratorType.NONE, ModelSize.SMALL,
        {
            'models': _models('qwen3:1.7b', 'llama3.2:3b'),
            'thinking': _models('qwen3:1.7b', 'deepseek-r1:1.5b'),
            'tools': _models('qwen3:1.7b', 'llama3.2:3b'),
            'vision': _models('moondream:1.8b', 'minicpm-v:3b'),
        },
        'q4_k_m', 1, 8192, 'Very Slow (CPU only)',
    ),
    ModelCatalogEntry(
        AcceleratorType.NONE, ModelSize.MEDIUM,
        {
            'models': _models('qwen3:8b', 'mistral:7b', 'llama3.1:8b'),
            'thinking': _models('qwen3:8b', 'deepseek-r1:8b'),
            'tools': _models('qwen3:8b', 'mistral:7b', 'llama3.1:8b'),
            'vision': _models('llava:7b', 'qwen2.5vl:7b', 'minicpm-v:8b'),
        },
        'q4_k_m', 1, 8192, 'Very Slow (CPU only)',
    ),
])
