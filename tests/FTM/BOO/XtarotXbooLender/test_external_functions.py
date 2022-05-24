from itertools import count
from brownie import Wei, config, reverts, Contract
import brownie

# tests that cloneGenericXboo works
def test_clone_generic_xboo(
    accounts,
    GenericXboo,
    strategy,
    kae_pid,
    masterchef,
    kae,
    kae_swapFirstStep,
    pm,
    guardian,
    boo,
    gov,
    rewards,
    Strategy,
    keeper,
    whale,
    amount,
    chain
):
    # deploy the vault
    Vault = pm(config["dependencies"][0]).Vault
    vault = Vault.deploy({"from": guardian})
    vault.initialize(boo, gov, rewards, "", "")
    vault.setDepositLimit(2**256-1, {"from": gov})

    # deploy the strategy and plugin
    strategist = accounts[2]
    strategy = strategist.deploy(Strategy, vault)
    strategy.setKeeper(keeper)
    kaePlugin = strategist.deploy(GenericXboo, strategy, kae_pid, "KaeXboo", masterchef, kae, kae_swapFirstStep, True)
    strategy.addLender(kaePlugin, {"from": gov})

    # add strategy to vault and whale deposits 15,000 BOO
    deposit_limit = 10_000
    vault.addStrategy(strategy, deposit_limit, 0, 2 ** 256 - 1, 1000, {"from": gov})
    boo.approve(vault, 2 ** 256 - 1, {"from": whale})
    whale_deposit = amount
    vault.deposit(whale_deposit, {"from": whale})
    chain.sleep(10)
    chain.mine(1)
    strategy.setWithdrawalThreshold(0, {"from": gov})
    strategy.harvest({"from": strategist})

    # clone the plugin
    _strategy = strategy
    _pid = 36
    _name = "PgkXboo"
    _masterchef = Contract("0x2352b745561e7e6FCD03c093cE7220e3e126ace0")
    _emissionToken = Contract("0x188a168280589bC3E483d77aae6b4A1d26bD22dC")
    _swapFirstStep = Contract("0x04068DA6C83AFCFA0e13ba15A6696662335D5B75")
    _autoSell = True
    t1 = kaePlugin.cloneGenericXboo(_strategy, _pid, _name, _masterchef, _emissionToken, _swapFirstStep, _autoSell, {"from": gov})
    pgkPlugin = GenericXboo.at(t1.events["Cloned"]["clone"])
    strategy.addLender(pgkPlugin, {"from": gov})


# tests that withdraw can't be called by anyone but the strategy
def test_withdraw(
    accounts,
    GenericXboo,
    strategy,
    kae_pid,
    masterchef,
    kae,
    kae_swapFirstStep,
    plugin
):
    # strategist = accounts[2]
    # kaePlugin = strategist.deploy(GenericXboo, strategy, kae_pid, "KaeXboo", masterchef, kae, kae_swapFirstStep, True)

    vault = Contract(plugin.vault())
    gov = accounts.at(vault.governance(), force=True)
    random_wallet = Contract("0x20dd72Ed959b6147912C2e529F0a0C651c33c9ce")
    
    with brownie.reverts("!management"):
        plugin.withdraw(10, {'from': random_wallet})


# tests that emergencyManualWithdraw can't be called by anyone but the strategy and then that it works when called by gov
def test_emergency_manual_withdraw(
    xboo,
    accounts,
    GenericXboo,
    strategy,
    kae_pid,
    masterchef,
    kae,
    kae_swapFirstStep,
    pm,
    guardian,
    boo,
    gov,
    rewards,
    Strategy,
    keeper,
    whale,
    amount,
    chain
):
    # deploy the vault
    Vault = pm(config["dependencies"][0]).Vault
    vault = Vault.deploy({"from": guardian})
    vault.initialize(boo, gov, rewards, "", "")
    vault.setDepositLimit(2**256-1, {"from": gov})

    # deploy the strategy and plugin
    strategist = accounts[2]
    strategy = strategist.deploy(Strategy, vault)
    strategy.setKeeper(keeper)
    kaePlugin = strategist.deploy(GenericXboo, strategy, kae_pid, "KaeXboo", masterchef, kae, kae_swapFirstStep, True)
    strategy.addLender(kaePlugin, {"from": gov})

    # add strategy to vault and whale deposits 15,000 BOO
    deposit_limit = 10_000
    vault.addStrategy(strategy, deposit_limit, 0, 2 ** 256 - 1, 1000, {"from": gov})
    boo.approve(vault, 2 ** 256 - 1, {"from": whale})
    whale_deposit = amount
    vault.deposit(whale_deposit, {"from": whale})
    chain.sleep(10)
    chain.mine(1)
    strategy.setWithdrawalThreshold(0, {"from": gov})
    strategy.harvest({"from": strategist})

    gov = accounts.at(vault.governance(), force=True)
    random_wallet = Contract("0x20dd72Ed959b6147912C2e529F0a0C651c33c9ce")
    
    with brownie.reverts():
        kaePlugin.emergencyManualWithdraw({'from': random_wallet})

    balance_before = xboo.balanceOf(kaePlugin)
    print(balance_before / 1e18)
    kaePlugin.emergencyManualWithdraw({'from': gov})
    balance_after = xboo.balanceOf(kaePlugin)
    print(balance_after / 1e18)
    assert balance_after > balance_before


# tests that emergencyWithdraw can't be called by anyone but the strategy and then that it works when called by gov
def test_emergency_withdraw(
    xboo,
    accounts,
    GenericXboo,
    strategy,
    kae_pid,
    masterchef,
    kae,
    kae_swapFirstStep,
    pm,
    guardian,
    boo,
    gov,
    rewards,
    Strategy,
    keeper,
    whale,
    amount,
    chain
):
    # deploy the vault
    Vault = pm(config["dependencies"][0]).Vault
    vault = Vault.deploy({"from": guardian})
    vault.initialize(boo, gov, rewards, "", "")
    vault.setDepositLimit(2**256-1, {"from": gov})

    # deploy the strategy and plugin
    strategist = accounts[2]
    strategy = strategist.deploy(Strategy, vault)
    strategy.setKeeper(keeper)
    kaePlugin = strategist.deploy(GenericXboo, strategy, kae_pid, "KaeXboo", masterchef, kae, kae_swapFirstStep, True)
    strategy.addLender(kaePlugin, {"from": gov})

    # add strategy to vault and whale deposits 15,000 BOO
    deposit_limit = 10_000
    vault.addStrategy(strategy, deposit_limit, 0, 2 ** 256 - 1, 1000, {"from": gov})
    boo.approve(vault, 2 ** 256 - 1, {"from": whale})
    whale_deposit = amount
    vault.deposit(whale_deposit, {"from": whale})
    chain.sleep(10)
    chain.mine(1)
    strategy.setWithdrawalThreshold(0, {"from": gov})
    strategy.harvest({"from": strategist})

    gov = accounts.at(vault.governance(), force=True)
    random_wallet = Contract("0x20dd72Ed959b6147912C2e529F0a0C651c33c9ce")
    
    with brownie.reverts():
        kaePlugin.emergencyWithdraw(100, {'from': random_wallet})
    
    balance_before = xboo.balanceOf(gov)
    print(balance_before / 1e18)
    kaePlugin.emergencyWithdraw(100, {'from': gov})
    balance_after = xboo.balanceOf(gov)
    print(balance_after / 1e18)
    assert balance_after > balance_before


# tests that claimRewards can't be called by anyone but the strategy
def test_claim_rewards(
    vault,
    accounts,
    GenericXboo,
    strategy,
    kae_pid,
    masterchef,
    kae,
    kae_swapFirstStep,
):
    strategist = accounts[2]
    kaePlugin = strategist.deploy(GenericXboo, strategy, kae_pid, "KaeXboo", masterchef, kae, kae_swapFirstStep, True)

    # vault = Contract(kaePlugin.vault())
    # gov = accounts.at(vault.governance(), force=True)
    random_wallet = Contract("0x20dd72Ed959b6147912C2e529F0a0C651c33c9ce")
    
    with brownie.reverts():
        kaePlugin.claimRewards({'from': random_wallet})


# tests that deposit can't be called by anyone but the strategy
def test_deposit(
    vault,
    accounts,
    GenericXboo,
    strategy,
    kae_pid,
    masterchef,
    kae,
    kae_swapFirstStep,
):
    strategist = accounts[2]
    kaePlugin = strategist.deploy(GenericXboo, strategy, kae_pid, "KaeXboo", masterchef, kae, kae_swapFirstStep, True)

    # vault = Contract(kaePlugin.vault())
    # gov = accounts.at(vault.governance(), force=True)
    random_wallet = Contract("0x20dd72Ed959b6147912C2e529F0a0C651c33c9ce")
    
    with brownie.reverts():
        kaePlugin.deposit({'from': random_wallet})


# tests that withdrawAll can't be called by anyone but the strategy
def test_withdraw_all(
    vault,
    accounts,
    GenericXboo,
    strategy,
    kae_pid,
    masterchef,
    kae,
    kae_swapFirstStep,
):
    strategist = accounts[2]
    kaePlugin = strategist.deploy(GenericXboo, strategy, kae_pid, "KaeXboo", masterchef, kae, kae_swapFirstStep, True)

    # vault = Contract(kaePlugin.vault())
    # gov = accounts.at(vault.governance(), force=True)
    random_wallet = Contract("0x20dd72Ed959b6147912C2e529F0a0C651c33c9ce")
    
    with brownie.reverts():
        kaePlugin.withdrawAll({'from': random_wallet})


# tests that manualSell can't be called by anyone but the strategy and then that it works when called by gov
def test_manual_sell(
    accounts,
    GenericXboo,
    strategy,
    kae_pid,
    masterchef,
    kae,
    kae_swapFirstStep,
    boo,
    gov,
):
    strategist = accounts[2]
    kaePlugin = strategist.deploy(GenericXboo, strategy, kae_pid, "KaeXboo", masterchef, kae, kae_swapFirstStep, True)
    
    # our kae whale transfers KAE to the plugin to simulate claimed emission tokens
    kaeWhale = accounts.at("0xeB8Ac7a87D22f541e6cf2E3dB0f36388e158F7Df", force=True)
    kae.transfer(kaePlugin, 10, {"from": kaeWhale})

    random_wallet = Contract("0x20dd72Ed959b6147912C2e529F0a0C651c33c9ce")
    
    with brownie.reverts():
        kaePlugin.manualSell(10, {'from': random_wallet})
    
    kae_balance_before = kae.balanceOf(kaePlugin)
    print("kae_balance_before", kae_balance_before / 1e18)
    boo_balance_before = boo.balanceOf(kaePlugin)
    print("boo_balance_before", boo_balance_before / 1e18)

    kaePlugin.manualSell(10, {'from': gov})

    kae_balance_after = kae.balanceOf(kaePlugin)
    print("kae_balance_after", kae_balance_after / 1e18)
    boo_balance_after = boo.balanceOf(kaePlugin)
    print("boo_balance_after", boo_balance_after / 1e18)

    assert boo_balance_after > boo_balance_before


# tests that setAutoSell can't be called by anyone but the strategy and then that it works when called by gov
def test_set_auto_sell(
    accounts,
    GenericXboo,
    strategy,
    kae_pid,
    masterchef,
    kae,
    kae_swapFirstStep,
    gov,
):
    strategist = accounts[2]
    kaePlugin = strategist.deploy(GenericXboo, strategy, kae_pid, "KaeXboo", masterchef, kae, kae_swapFirstStep, True)
    random_wallet = Contract("0x20dd72Ed959b6147912C2e529F0a0C651c33c9ce")
    
    with brownie.reverts():
        kaePlugin.setAutoSell(False, {'from': random_wallet})
    
    # Turn off autoSell
    kaePlugin.setAutoSell(False, {'from': gov})
    assert kaePlugin.autoSell() == False

    # Turn on autoSell
    kaePlugin.setAutoSell(True, {'from': gov})
    assert kaePlugin.autoSell() == True


# tests that setMaxSell can't be called by anyone but the strategy and then that it works when called by gov
def test_set_max_sell(
    accounts,
    GenericXboo,
    strategy,
    kae_pid,
    masterchef,
    kae,
    kae_swapFirstStep,
    gov,
):
    strategist = accounts[2]
    kaePlugin = strategist.deploy(GenericXboo, strategy, kae_pid, "KaeXboo", masterchef, kae, kae_swapFirstStep, True)
    random_wallet = Contract("0x20dd72Ed959b6147912C2e529F0a0C651c33c9ce")
    
    with brownie.reverts():
        kaePlugin.setMaxSell(100, {'from': random_wallet})
    
    # Turn off autoSell
    kaePlugin.setMaxSell(100, {'from': gov})
    assert kaePlugin.maxSell() == 100


# tests that setUseSpiritOne can't be called by anyone but the strategy and then that it works when called by gov
def test_set_use_spirit_one(
    accounts,
    GenericXboo,
    strategy,
    kae_pid,
    masterchef,
    kae,
    kae_swapFirstStep,
    gov,
):
    strategist = accounts[2]
    kaePlugin = strategist.deploy(GenericXboo, strategy, kae_pid, "KaeXboo", masterchef, kae, kae_swapFirstStep, True)
    random_wallet = Contract("0x20dd72Ed959b6147912C2e529F0a0C651c33c9ce")
    
    with brownie.reverts():
        kaePlugin.setUseSpiritOne(True, {'from': random_wallet})
    
    # Turn off autoSell
    kaePlugin.setUseSpiritOne(True, {'from': gov})
    assert kaePlugin.useSpiritPartOne() == True

    # Turn on autoSell
    kaePlugin.setUseSpiritOne(False, {'from': gov})
    assert kaePlugin.useSpiritPartOne() == False


# tests that setUseSpiritTwo can't be called by anyone but the strategy and then that it works when called by gov
def test_set_use_spirit_two(
    accounts,
    GenericXboo,
    strategy,
    kae_pid,
    masterchef,
    kae,
    kae_swapFirstStep,
    gov,
):
    strategist = accounts[2]
    kaePlugin = strategist.deploy(GenericXboo, strategy, kae_pid, "KaeXboo", masterchef, kae, kae_swapFirstStep, True)
    random_wallet = Contract("0x20dd72Ed959b6147912C2e529F0a0C651c33c9ce")
    
    with brownie.reverts():
        kaePlugin.setUseSpiritTwo(True, {'from': random_wallet})
    
    # Turn off autoSell
    kaePlugin.setUseSpiritTwo(True, {'from': gov})
    assert kaePlugin.useSpiritPartTwo() == True

    # Turn on autoSell
    kaePlugin.setUseSpiritTwo(False, {'from': gov})
    assert kaePlugin.useSpiritPartTwo() == False