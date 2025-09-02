<div align="center">

# GENII
**A powerful neurophysiology data processing and visualization platform.**

<p align="center">
  <a href="https://github.com/jhpuah/EEGDM/blob/main/EEGDM_V2.pdf">
    <img
      src="https://img.shields.io/badge/EEGDM-Paper-red?logo=arxiv&logoColor=red"
      alt="EEGDM Paper on arXiv"
    />
  </a>
  <a href="https://huggingface.co/jhpuah/eegdm/tree/main">
    <img 
        src="https://img.shields.io/badge/EEGDM-Hugging%20Face%20Model-orange?logo=huggingface&logoColor=yellow" 
        alt="EEGDM on Hugging Face"
    />
  </a>
</p>

![ComfyUI Screenshot](https://github.com/user-attachments/assets/7ccaf2c1-9b72-41ae-9a89-5688c94b7abe)

</div>

Genii-Python enables you to process, analyze, and visualize neurophysiological data, offering user authentication, file upload, data processing, and interactive data visualization functionalities.

## Features
- It utilizes the mne-python library for data analysis and provides user authentication, file upload, data processing (such as filtering, reference electrode setup), and interactive data visualization functions.
- User Authentication
- File upload
- Data processing
- Interactive data visualization
- Data saving
- Modular design

# Quick Start

## Environment Preparation

```
conda create -n GENII pip python=3.10.12
conda activate GENII
git clone https://github.com/genii-open/genii-python.git
pip install -r requirements.txt
```

### Run

```
python app.py
```

By default, the program will run in debug mode and listen on port 8892. You can access it via a browser at http://127.0.0.1:8892.

# Guidance

After typing
```
python app.py
```
in conda environment, access it via a browser at http://127.0.0.1:8892.

### Log In

<div align="center">
<br>
<img src="assets/login.png" width="966">
</div>
<br>

Log in using the email and password that we provided to you.

### File Upload

You can enable experimental memory efficient attention on recent pytorch in ComfyUI on some AMD GPUs using this command, it should already be enabled by default on RDNA3. If this improves speed for you on latest pytorch on your GPU please report it so that I can enable it by default.

```TORCH_ROCM_AOTRITON_ENABLE_EXPERIMENTAL=1 python main.py --use-pytorch-cross-attention```

You can also try setting this env variable `PYTORCH_TUNABLEOP_ENABLED=1` which might speed things up at the cost of a very slow initial run.

### Data Visualization

You can enable experimental memory efficient attention on recent pytorch in ComfyUI on some AMD GPUs using this command, it should already be enabled by default on RDNA3. If this improves speed for you on latest pytorch on your GPU please report it so that I can enable it by default.

```TORCH_ROCM_AOTRITON_ENABLE_EXPERIMENTAL=1 python main.py --use-pytorch-cross-attention```

You can also try setting this env variable `PYTORCH_TUNABLEOP_ENABLED=1` which might speed things up at the cost of a very slow initial run.

### Data Processing

You can enable experimental memory efficient attention on recent pytorch in ComfyUI on some AMD GPUs using this command, it should already be enabled by default on RDNA3. If this improves speed for you on latest pytorch on your GPU please report it so that I can enable it by default.

```TORCH_ROCM_AOTRITON_ENABLE_EXPERIMENTAL=1 python main.py --use-pytorch-cross-attention```

You can also try setting this env variable `PYTORCH_TUNABLEOP_ENABLED=1` which might speed things up at the cost of a very slow initial run.

### Data Saving

You can enable experimental memory efficient attention on recent pytorch in ComfyUI on some AMD GPUs using this command, it should already be enabled by default on RDNA3. If this improves speed for you on latest pytorch on your GPU please report it so that I can enable it by default.

```TORCH_ROCM_AOTRITON_ENABLE_EXPERIMENTAL=1 python main.py --use-pytorch-cross-attention```

You can also try setting this env variable `PYTORCH_TUNABLEOP_ENABLED=1` which might speed things up at the cost of a very slow initial run.

# Notes

Only parts of the graph that have an output with all the correct inputs will be executed.

Only parts of the graph that change from each execution to the next will be executed, if you submit the same graph twice only the first will be executed. If you change the last part of the graph only the part you changed and the part that depends on it will be executed.

Dragging a generated png on the webpage or loading one will give you the full workflow including seeds that were used to create it.

You can use () to change emphasis of a word or phrase like: (good code:1.2) or (bad code:0.8). The default emphasis for () is 1.1. To use () characters in your actual prompt escape them like \\( or \\).

You can use {day|night}, for wildcard/dynamic prompts. With this syntax "{wild|card|test}" will be randomly replaced by either "wild", "card" or "test" by the frontend every time you queue the prompt. To use {} characters in your actual prompt escape them like: \\{ or \\}.

Dynamic prompts also support C-style comments, like `// comment` or `/* comment */`.

To use a textual inversion concepts/embeddings in a text prompt put them in the models/embeddings directory and use them in the CLIPTextEncode node like this (you can omit the .pt extension):

```embedding:embedding_filename.pt```


## How to show high-quality previews?

Use ```--preview-method auto``` to enable previews.

The default installation includes a fast latent preview method that's low-resolution. To enable higher-quality previews with [TAESD](https://github.com/madebyollin/taesd), download the [taesd_decoder.pth, taesdxl_decoder.pth, taesd3_decoder.pth and taef1_decoder.pth](https://github.com/madebyollin/taesd/) and place them in the `models/vae_approx` folder. Once they're installed, restart ComfyUI and launch it with `--preview-method taesd` to enable high-quality previews.

## How to use TLS/SSL?
Generate a self-signed certificate (not appropriate for shared/production use) and key by running the command: `openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -sha256 -days 3650 -nodes -subj "/C=XX/ST=StateName/L=CityName/O=CompanyName/OU=CompanySectionName/CN=CommonNameOrHostname"`

Use `--tls-keyfile key.pem --tls-certfile cert.pem` to enable TLS/SSL, the app will now be accessible with `https://...` instead of `http://...`.

> Note: Windows users can use [alexisrolland/docker-openssl](https://github.com/alexisrolland/docker-openssl) or one of the [3rd party binary distributions](https://wiki.openssl.org/index.php/Binaries) to run the command example above.
<br/><br/>If you use a container, note that the volume mount `-v` can be a relative path so `... -v ".\:/openssl-certs" ...` would create the key & cert files in the current directory of your command prompt or powershell terminal.

## Support and dev channel

[Discord](https://comfy.org/discord): Try the #help or #feedback channels.

[Matrix space: #comfyui_space:matrix.org](https://app.element.io/#/room/%23comfyui_space%3Amatrix.org) (it's like discord but open source).

See also: [https://www.comfy.org/](https://www.comfy.org/)

## Frontend Development

As of August 15, 2024, we have transitioned to a new frontend, which is now hosted in a separate repository: [ComfyUI Frontend](https://github.com/Comfy-Org/ComfyUI_frontend). This repository now hosts the compiled JS (from TS/Vue) under the `web/` directory.

### Reporting Issues and Requesting Features

For any bugs, issues, or feature requests related to the frontend, please use the [ComfyUI Frontend repository](https://github.com/Comfy-Org/ComfyUI_frontend). This will help us manage and address frontend-specific concerns more efficiently.

### Using the Latest Frontend

The new frontend is now the default for ComfyUI. However, please note:

1. The frontend in the main ComfyUI repository is updated fortnightly.
2. Daily releases are available in the separate frontend repository.

To use the most up-to-date frontend version:

1. For the latest daily release, launch ComfyUI with this command line argument:

   ```
   --front-end-version Comfy-Org/ComfyUI_frontend@latest
   ```

2. For a specific version, replace `latest` with the desired version number:

   ```
   --front-end-version Comfy-Org/ComfyUI_frontend@1.2.2
   ```

This approach allows you to easily switch between the stable fortnightly release and the cutting-edge daily updates, or even specific versions for testing purposes.

### Accessing the Legacy Frontend

If you need to use the legacy frontend for any reason, you can access it using the following command line argument:

```
--front-end-version Comfy-Org/ComfyUI_legacy_frontend@latest
```

This will use a snapshot of the legacy frontend preserved in the [ComfyUI Legacy Frontend repository](https://github.com/Comfy-Org/ComfyUI_legacy_frontend).

# QA

### Which GPU should I buy for this?

[See this page for some recommendations](https://github.com/comfyanonymous/ComfyUI/wiki/Which-GPU-should-I-buy-for-ComfyUI)
