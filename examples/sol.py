import warnings

warnings.filterwarnings("ignore")

import arviz as az
import jax.numpy as jnp
import matplotlib.pyplot as plt
import numpyro
import numpyro.distributions as dist
import pandas as pd
from numpyro.diagnostics import hpdi

from numpyro_oop import BaseNumpyroModel

import wandb



# TODO: log the experiment settings to wandb
hyperparams = {
    'seed': 42,
    'platform': 'cpu',
    'device_count': 4

}

# TODO: initialize the Weights & Biases run
run = wandb.init(project='ws-test', name='numpyro_oop', config=hyperparams)

numpyro.set_platform(hyperparams['platform'])
numpyro.set_host_device_count(hyperparams['device_count'])
DATASET_URL = "https://raw.githubusercontent.com/rmcelreath/rethinking/master/data/WaffleDivorce.csv"
dset = pd.read_csv(DATASET_URL, sep=";")

def standardize(x):
    return (x - x.mean()) / x.std()

dset["AgeScaled"] = dset.MedianAgeMarriage.pipe(standardize)
dset["MarriageScaled"] = dset.Marriage.pipe(standardize)
dset["DivorceScaled"] = dset.Divorce.pipe(standardize)

# TODO: create an artifact object and log the dataset
table = wandb.Table(dataframe=dset)
run.log({'data': table})

def plot_regression(x, y_mean, y_hpdi):
    # Sort values for plotting by x axis
    idx = jnp.argsort(x)
    marriage = x[idx]
    mean = y_mean[idx]
    hpdi = y_hpdi[:, idx]
    divorce = dset.DivorceScaled.values[idx]

    # Plot
    fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(6, 6))
    ax.plot(marriage, mean)
    ax.plot(marriage, divorce, "o")
    ax.fill_between(marriage, hpdi[0], hpdi[1], alpha=0.3, interpolate=True)
    return fig, ax

class RegressionModel(BaseNumpyroModel):
    def model(self, data=None, sample_conditional=True):
        a = numpyro.sample("a", dist.Normal(0.0, 0.2))
        bM = numpyro.sample("bM", dist.Normal(0.0, 0.5))
        M = bM * data.MarriageScaled.values
        sigma = numpyro.sample("sigma", dist.Exponential(1.0))
        mu = numpyro.deterministic("mu", a + M)

        if sample_conditional:
            obs = data.DivorceScaled.values
        else:
            obs = None

        numpyro.sample("obs", dist.Normal(mu, sigma), obs=obs)

m1 = RegressionModel(data=dset, seed=hyperparams['seed'])
m1.render()
m1.sample(generate_arviz_data=True)
m1.mcmc.print_summary(0.90)

# TODO: log predictions
preds = m1.predict()
mean_mu = preds["mu"].mean(axis=0)
hpdi_mu = hpdi(preds["mu"], 0.9)
run.log({'predictions': preds})

# TODO: log all figure objects to Weights & Biases
fig, ax = plot_regression(dset.MarriageScaled.values, mean_mu, hpdi_mu)
ax.set(
    xlabel="Marriage rate", ylabel="Divorce rate", title="Regression line with 90% CI"
)
run.log({'regression': fig})

preds = m1.predict(prior=True, model_kwargs={"sample_conditional": False})
mean_prior_pred = preds["obs"].mean(axis=0)
hpdi_prior_pred = hpdi(preds["obs"], 0.9)
fig, ax = plot_regression(dset.MarriageScaled.values, mean_prior_pred, hpdi_prior_pred)
ax.set(
    xlabel="Marriage rate", ylabel="Divorce rate", title="Prior predictions with 90% CI"
)
run.log({'prior': fig})

preds = m1.predict(prior=False, model_kwargs={"sample_conditional": False})
mean_post_pred = preds["obs"].mean(axis=0)
hpdi_post_pred = hpdi(preds["obs"], 0.9)
fig, ax = plot_regression(dset.MarriageScaled.values, mean_post_pred, hpdi_post_pred)
ax.set(
    xlabel="Marriage rate",
    ylabel="Divorce rate",
    title="Posterior predictions with 90% CI",
)
run.log({'posterior': fig})

fig, ax = plt.subplots(1, 1, figsize=(6, 4), layout="constrained")
ax = az.plot_forest(
    [m1.arviz_data["posterior"], m1.arviz_data["prior"]],
    model_names=["posterior", "prior"],
    kind="forestplot",
    var_names=["a", "bM", "sigma"],
    hdi_prob=0.9,
    combined=True,
    ridgeplot_overlap=1.5,
    ax=ax,
)
ax[0].set_title("Model parameters")
run.log({'forest': fig})
