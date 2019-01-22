# flogger

Flogger is a data logging tool that tries to provide a simple and unified interface to various logging solutions one may
want to use in deep-learning experiments. Put differently, it allows to store various types of data an experiment can
generate (images, curves, text, videos, ...), into various forms (Json, matplotlib figures, tensorboard logs, etc...).
As far as it can go with python, the handling of data is made asynchronously, to avoid blocking the experiment thread.

## Install

```bash
pip install git+https://github.com/aPere3/flogger.git
```

## Documentation

For more information, see [the documentation](https://apere3.github.io/flogger).
