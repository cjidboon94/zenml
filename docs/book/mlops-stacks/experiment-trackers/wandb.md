---
description: How to log and visualize experiments with Weights & Biases
---

The Weights & Biases Experiment Tracker is an [Experiment Tracker](./experiment-trackers.md)
flavor provided with the Weights & Biases ZenML integration that uses
[the Weights & Biases experiment tracking platform](https://wandb.ai/site/experiment-tracking)
to log and visualize information from your pipeline steps (e.g. models, parameters,
metrics).

## When would you want to use it?

[Weights & Biases](https://wandb.ai/site/experiment-tracking) is a very
popular platform that you would normally use in the iterative ML experimentation
phase to track and visualize experiment results. That doesn't mean that it
cannot be repurposed to track and visualize the results produced by your
automated pipeline runs, as you make the transition towards a more production
oriented workflow.

You should use the Weights & Biases Experiment Tracker:
* if you have already been using Weights & Biases to track experiment results
for your project and would like to continue doing so as you are incorporating MLOps
workflows and best practices in your project through ZenML.
* if you are looking for a more visually interactive way of navigating the
results produced from your ZenML pipeline runs (e.g. models, metrics, datasets)
* if you would like to connect ZenML to Weights & Biases to share the artifacts
and metrics logged by your pipelines with your team, organization or external
stakeholders

You should consider one of the other [Experiment Tracker flavors](./experiment-trackers.md#experiment-tracker-flavors)
if you have never worked with Weights & Biases before and would rather use
another experiment tracking tool that you are more familiar with.

## How do you deploy it?

The Weights & Biases Experiment Tracker flavor is provided by the MLflow ZenML
integration, you need to install it on your local machine to be able to register
a Weights & Biases Experiment Tracker and add it to your stack:

```shell
zenml integration install wandb -y
```

The Weights & Biases Experiment Tracker needs to be configured with the
credentials required to connect to the Weights & Biases platform using one
of the [available authentication methods](#authentication-methods).

### Authentication Methods

You need to configure the following credentials for authentication to the
Weights & Biases platform:

* `api_key`: Mandatory API key token of your Weights & Biases account.
* `project_name`: The name of the project where you're sending the new run. If
the project is not specified, the run is put in an "Uncategorized" project.
* `entity`: An entity is a username or team name where you're sending runs. This
entity must exist before you can send runs there, so make sure to create your
account or team in the UI before starting to log runs. If you don't specify an
entity, the run will be sent to your default entity, which is usually your
username. 

{% tabs %}
{% tab title="Basic Authentication" %}

This option configures the credentials for the Weights & Biases platform
directly as stack component attributes.

{% hint style="warning" %}
This is not recommended for production settings as the credentials won't be
stored securely and will be clearly visible in the stack configuration.
{% endhint %}

```shell
# Register the Weights & Biases experiment tracker
zenml experiment-tracker register wandb_experiment_tracker --flavor=wandb \ 
    --entity=<entity> --project_name=<project_name> --api_key=<key>

# Register and set a stack with the new experiment tracker
zenml stack register custom_stack -e wandb_experiment_tracker ... --set
```
{% endtab %}

{% tab title="Secrets Manager (Recommended)" %}

This method requires you to include a [Secrets Manager](../secrets-managers/secrets-managers.md)
in your stack and configure a ZenML secret to store the Weights & Biases
credentials securely.

{% hint style="warning" %}
**This method is not yet supported!**

We are actively working on adding Secrets Manager support to the Weights & Biases
Experiment Tracker.
{% endhint %}
{% endtab %}
{% endtabs %}

For more, up-to-date information on the Weights & Biases Experiment Tracker
implementation and its configuration, you can have a look at [the API docs](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.wandb.experiment_trackers.wandb_experiment_tracker).

## How do you use it?

To be able to log information from a ZenML pipeline step using the Weights &
Biases Experiment Tracker component in the active stack, you need to use the
`enable_wandb` step decorator on all pipeline steps where you plan on doing
that. Then use the Weights & Biases logging or auto-logging capabilities
as you would normally do, e.g.:

```python
import wandb
from wandb.integration.keras import WandbCallback
from zenml.integrations.wandb.wandb_step_decorator import enable_wandb

@enable_wandb
@step
def tf_trainer(
    config: TrainerConfig,
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_val: np.ndarray,
    y_val: np.ndarray,
) -> tf.keras.Model:
    
    ...

    model.fit(
        x_train,
        y_train,
        epochs=config.epochs,
        validation_data=(x_val, y_val),
        callbacks=[
            WandbCallback(
                log_evaluation=True,
                validation_steps=16,
                validation_data=(x_val, y_val),
            )
        ],
    )

    ...
```

ZenML allows you to override the [wandb.Settings](https://github.com/wandb/client/blob/master/wandb/sdk/wandb_settings.py#L353) 
class in the `enable_wandb` decorator to allow for even further control of the
Weights & Biases integration. One feature that is super useful is to enable
`magic=True`, like so:

```python
import wandb

@enable_wandb(settings=wandb.Settings(magic=True))
@step
def my_step(
        x_test: np.ndarray,
        y_test: np.ndarray,
        model: tf.keras.Model,
) -> float:
    """Everything in this step is autologged"""
    ...
```

Doing the above auto-magically logs all the data, metrics, and results within
the step, no further action required!

You can also check out our examples pages for working examples that use the
Weights & Biases Experiment Tracker in their stacks:

- [Track Experiments with Weights & Biases](https://github.com/zenml-io/zenml/tree/main/examples/wandb_tracking)
