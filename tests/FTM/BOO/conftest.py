import pytest
from brownie import Wei, config, Contract
import requests
# Snapshots the chain before each test and reverts after test completion.
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass

# @pytest.fixture(scope="module", autouse=True)
def tenderly_fork(web3):
    fork_base_url = "https://simulate.yearn.network/fork"
    payload = {"network_id": "250"}
    resp = requests.post(fork_base_url, headers={}, json=payload)
    fork_id = resp.json()["simulation_fork"]["id"]
    fork_rpc_url = f"https://rpc.tenderly.co/fork/{fork_id}"
    print(fork_rpc_url)
    tenderly_provider = web3.HTTPProvider(fork_rpc_url, {"timeout": 600})
    web3.provider = tenderly_provider
    print(f"https://dashboard.tenderly.co/yearn/yearn-web/fork/{fork_id}")

# this is the pool ID that we are staking for. 21, hec
@pytest.fixture(scope="module")
def pid():
    pid = 21
    yield pid


# this is the name we want to give our strategy
@pytest.fixture(scope="module")
def strategy_name():
    strategy_name = "XbooStaker"
    yield strategy_name


@pytest.fixture(scope="module")
def wftm():
    yield Contract("0x21be370D5312f44cB42ce377BC9b8a0cEF1A4C83")


@pytest.fixture(scope="module")
def weth():
    yield Contract("0x74b23882a30290451A17c44f4F05243b6b58C76d")


@pytest.fixture(scope="module")
def wbtc():
    yield Contract("0x321162Cd933E2Be498Cd2267a90534A804051b11")


@pytest.fixture(scope="module")
def dai():
    yield Contract("0x8D11eC38a3EB5E956B052f67Da8Bdc9bef8Abf3E")


@pytest.fixture(scope="module")
def usdc():
    yield Contract("0x04068DA6C83AFCFA0e13ba15A6696662335D5B75")


@pytest.fixture(scope="module")
def mim():
    yield Contract("0x82f0B8B456c1A451378467398982d4834b6829c1")


@pytest.fixture(scope="module")
def boo():
    yield Contract("0x841FAD6EAe12c286d1Fd18d1d525DFfA75C7EFFE")

@pytest.fixture(scope="module")
def kae():
    yield Contract("0x65Def5029A0e7591e46B38742bFEdd1Fb7b24436")

@pytest.fixture(scope="module")
def kae_pid():
    yield 28
@pytest.fixture(scope="module")
def kae_swapFirstStep(wftm):
    yield wftm

@pytest.fixture(scope="module")
def bftm():
    yield Contract("0x7381eD41F6dE418DdE5e84B55590422a57917886")

@pytest.fixture(scope="module")
def bftm_pid():
    yield 32
@pytest.fixture(scope="module")
def bftm_swapFirstStep(wftm):
    yield wftm

@pytest.fixture(scope="module")
def mst():
    yield Contract("0x152888854378201e173490956085c711f1DeD565")

@pytest.fixture(scope="module")
def mst_pid():
    yield 26
@pytest.fixture(scope="module")
def mst_swapFirstStep(wftm):
    yield wftm

@pytest.fixture(scope="module")
def xboo():
    yield Contract("0xa48d959AE2E88f1dAA7D5F611E01908106dE7598")
@pytest.fixture(scope="module")
def masterchef():
    yield Contract("0x2352b745561e7e6FCD03c093cE7220e3e126ace0")

# Define relevant tokens and contracts in this section
@pytest.fixture(scope="module")
def token(boo):
    yield boo


@pytest.fixture(scope="module")
def whale(accounts, token, amount, strategist):
    # Update this with a large holder of your want token (the largest EOA holder of LP)
    whale = accounts.at("0x5804F6C40f44cF7593F73cf3aa16F7037213A623", force=True)
    token.transfer(strategist, amount, {'from': whale})
    yield whale


# this is the amount of funds we have our whale deposit. adjust this as needed based on their wallet balance
@pytest.fixture(scope="module")
def amount(token):  # use today's exchange rates to have similar $$ amounts
    amount = 15000 * (10 ** token.decimals())
    yield amount

@pytest.fixture(scope="module")
def rewards(gov):
    yield gov  # TODO: Add rewards contract

@pytest.fixture(scope="module")
def guardian(accounts):
    # YFI Whale, probably
    yield accounts[2]

@pytest.fixture(scope="module")
def gov(accounts):
    yield accounts[5]
@pytest.fixture(scope="module")
def strategist(accounts):
    # YFI Whale, probably
    yield accounts[2]

@pytest.fixture(scope="module")
def keeper(accounts):
    # This is our trusty bot!
    yield accounts[4]

@pytest.fixture(scope="module")
def live_vault(gov, accounts, Strategy, rewards, guardian, boo, pm):
    Vault = pm(config["dependencies"][0]).Vault
    vault = Vault.at('0x0fBbf9848D969776a5Eb842EdAfAf29ef4467698')
    gov = accounts.at(vault.governance(), force=True)
    old_strat = Strategy.at(vault.withdrawalQueue(0))
    vault.updateStrategyDebtRatio(old_strat, 0, {'from': gov})
    old_strat.harvest({'from': gov})

    assert old_strat.estimatedTotalAssets() < 1e16

    yield vault

@pytest.fixture(scope="module")
def live_strategy(
    live_vault,
    Strategy,
    GenericXboo,
    kae_pid,
    kae,
    kae_swapFirstStep,
    mst_pid,
    mst,
    mst_swapFirstStep,
    bftm_pid,
    bftm,
    bftm_swapFirstStep,
    masterchef,
    accounts
):
    strategy = Strategy.at('0x4CE40A36A018457F8E0AA7C4a12Cc7ebf228B20F')
    

    strategist = accounts.at(strategy.strategist(), force=True)
    gov = accounts.at(live_vault.governance(), force=True)



    # kaePlugin = strategist.deploy(GenericXboo, strategy, kae_pid, "KaeXboo", masterchef, kae, kae_swapFirstStep, True)
    lunaPlugin =  GenericXboo.at('0x7a1dE1a9ABF7Ff94E09d407E12fa70511443aFDF')
    # mstPlugin = strategist.deploy(GenericXboo, strategy, mst_pid, "MstXboo", masterchef, mst, mst_swapFirstStep, True)
    sdPlugin = GenericXboo.at('0x351E0449C24fA79CBd2A54B9fce52845A5c47276')

    # t1 = mstPlugin.cloneGenericXboo(strategy, bftm_pid, "BftmXboo", masterchef, bftm, bftm_swapFirstStep, True)
    # bftmPlugin = GenericXboo.at(t1.events["Cloned"]["clone"])
    bftmPlugin = GenericXboo.at('0x545b2C68d246A6E103C1C184e2e663c726963157')


    
    strategy.addLender(lunaPlugin, {"from": gov})
    strategy.addLender(sdPlugin, {"from": gov})
    strategy.addLender(bftmPlugin, {"from": gov})
    # assert strategy.numLenders() == 3
    yield strategy
    



@pytest.fixture(scope="module")
def vault(gov, rewards, guardian, boo, pm):
    Vault = pm(config["dependencies"][0]).Vault
    vault = Vault.deploy({"from": guardian})
    vault.initialize(boo, gov, rewards, "", "")
    vault.setDepositLimit(2**256-1, {"from": gov})

    yield vault

@pytest.fixture(scope="module")
def strategy(
    strategist,
    keeper,
    vault,
    gov,
    Strategy,
    GenericXboo,
    kae_pid,
    kae,
    kae_swapFirstStep,
    mst_pid,
    mst,
    mst_swapFirstStep,
    bftm_pid,
    bftm,
    bftm_swapFirstStep,
    masterchef
):
    strategy = strategist.deploy(Strategy, vault)
    strategy.setKeeper(keeper)


    kaePlugin = strategist.deploy(GenericXboo, strategy, kae_pid, "KaeXboo", masterchef, kae, kae_swapFirstStep, True)
    mstPlugin = strategist.deploy(GenericXboo, strategy, mst_pid, "MstXboo", masterchef, mst, mst_swapFirstStep, True)

    t1 = mstPlugin.cloneGenericXboo(strategy, bftm_pid, "BftmXboo", masterchef, bftm, bftm_swapFirstStep, True)
    bftmPlugin = GenericXboo.at(t1.events["Cloned"]["clone"])


    
    strategy.addLender(kaePlugin, {"from": gov})
    strategy.addLender(mstPlugin, {"from": gov})
    strategy.addLender(bftmPlugin, {"from": gov})
    assert strategy.numLenders() == 3
    yield strategy
