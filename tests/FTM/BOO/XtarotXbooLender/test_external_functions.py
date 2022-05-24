from itertools import count
from brownie import Wei, config, reverts, Contract
import brownie

# tests that cloneGenericXboo works
def test_clone_generic_xboo(
    accounts,
    GenericXbooXtarot,
    strategy,
    xtarot_pid,
    masterchef,
    xtarotRouter,
    xtarot,
    xtarot_swapFirstStep,
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
    xtarotPlugin = strategist.deploy(GenericXbooXtarot, strategy, xtarot_pid, "XtarotXboo", masterchef, xtarotRouter, xtarot, xtarot_swapFirstStep, True)
    strategy.addLender(xtarotPlugin, {"from": gov})

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
    GenericXbooXtarot,
    strategy,
    xtarot_pid,
    masterchef,
    xtarotRouter,
    xtarot,
    xtarot_swapFirstStep,
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
    xtarotPlugin = strategist.deploy(GenericXbooXtarot, strategy, xtarot_pid, "XtarotXboo", masterchef, xtarotRouter, xtarot, xtarot_swapFirstStep, True)
    strategy.addLender(xtarotPlugin, {"from": gov})

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
        xtarotPlugin.emergencyManualWithdraw({'from': random_wallet})

    balance_before = xboo.balanceOf(xtarotPlugin)
    print(balance_before / 1e18)
    xtarotPlugin.emergencyManualWithdraw({'from': gov})
    balance_after = xboo.balanceOf(xtarotPlugin)
    print(balance_after / 1e18)
    assert balance_after > balance_before


# tests that emergencyWithdraw can't be called by anyone but the strategy and then that it works when called by gov
def test_emergency_withdraw(
    xboo,
    accounts,
    GenericXbooXtarot,
    strategy,
    xtarot_pid,
    masterchef,
    xtarotRouter,
    xtarot,
    xtarot_swapFirstStep,
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
    xtarotPlugin = strategist.deploy(GenericXbooXtarot, strategy, xtarot_pid, "XtarotXboo", masterchef, xtarotRouter, xtarot, xtarot_swapFirstStep, True)
    strategy.addLender(xtarotPlugin, {"from": gov})

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
        xtarotPlugin.emergencyWithdraw(100, {'from': random_wallet})
    
    balance_before = xboo.balanceOf(gov)
    print(balance_before / 1e18)
    xtarotPlugin.emergencyWithdraw(100, {'from': gov})
    balance_after = xboo.balanceOf(gov)
    print(balance_after / 1e18)
    assert balance_after > balance_before


# tests that claimRewards can't be called by anyone but the strategy
def test_claim_rewards(
    vault,
    accounts,
    GenericXbooXtarot,
    strategy,
    xtarot_pid,
    masterchef,
    xtarotRouter,
    xtarot,
    xtarot_swapFirstStep,
):
    strategist = accounts[2]
    xtarotPlugin = strategist.deploy(GenericXbooXtarot, strategy, xtarot_pid, "XtarotXboo", masterchef, xtarotRouter, xtarot, xtarot_swapFirstStep, True)

    # vault = Contract(kaePlugin.vault())
    # gov = accounts.at(vault.governance(), force=True)
    random_wallet = Contract("0x20dd72Ed959b6147912C2e529F0a0C651c33c9ce")
    
    with brownie.reverts():
        xtarotPlugin.claimRewards({'from': random_wallet})


# tests that deposit can't be called by anyone but the strategy
def test_deposit(
    vault,
    accounts,
    GenericXbooXtarot,
    strategy,
    xtarot_pid,
    masterchef,
    xtarotRouter,
    xtarot,
    xtarot_swapFirstStep,
):
    strategist = accounts[2]
    xtarotPlugin = strategist.deploy(GenericXbooXtarot, strategy, xtarot_pid, "XtarotXboo", masterchef, xtarotRouter, xtarot, xtarot_swapFirstStep, True)

    # vault = Contract(kaePlugin.vault())
    # gov = accounts.at(vault.governance(), force=True)
    random_wallet = Contract("0x20dd72Ed959b6147912C2e529F0a0C651c33c9ce")
    
    with brownie.reverts():
        xtarotPlugin.deposit({'from': random_wallet})


# tests that withdrawAll can't be called by anyone but the strategy
def test_withdraw_all(
    vault,
    accounts,
    GenericXbooXtarot,
    strategy,
    xtarot_pid,
    masterchef,
    xtarotRouter,
    xtarot,
    xtarot_swapFirstStep,
):
    strategist = accounts[2]
    xtarotPlugin = strategist.deploy(GenericXbooXtarot, strategy, xtarot_pid, "XtarotXboo", masterchef, xtarotRouter, xtarot, xtarot_swapFirstStep, True)

    # vault = Contract(kaePlugin.vault())
    # gov = accounts.at(vault.governance(), force=True)
    random_wallet = Contract("0x20dd72Ed959b6147912C2e529F0a0C651c33c9ce")
    
    with brownie.reverts():
        xtarotPlugin.withdrawAll({'from': random_wallet})


# tests that manualSell can't be called by anyone but the strategy and then that it works when called by gov
def test_manual_sell(
    accounts,
    GenericXbooXtarot,
    strategy,
    xtarot_pid,
    masterchef,
    xtarotRouter,
    xtarot,
    xtarot_swapFirstStep,
    boo,
    gov,
):
    strategist = accounts[2]
    xtarotPlugin = strategist.deploy(GenericXbooXtarot, strategy, xtarot_pid, "XtarotXboo", masterchef, xtarotRouter, xtarot, xtarot_swapFirstStep, True)
    
    # our kae whale transfers KAE to the plugin to simulate claimed emission tokens
    xtarotWhale = accounts.at("0x0ED650C3185eF33b6F61aD2fA7521A3602DF566c", force=True)
    xtarot.transfer(xtarotPlugin, 10 * 1e18, {"from": xtarotWhale})

    random_wallet = Contract("0x20dd72Ed959b6147912C2e529F0a0C651c33c9ce")
    
    with brownie.reverts():
        xtarotPlugin.manualSell(10 * 1e18, {'from': random_wallet})
    
    xtarot_balance_before = xtarot.balanceOf(xtarotPlugin)
    print("xtarot_balance_before", xtarot_balance_before / 1e18)
    boo_balance_before = boo.balanceOf(xtarotPlugin)
    print("boo_balance_before", boo_balance_before / 1e18)

    xtarotPlugin.manualSell(10 * 1e18, {'from': gov})

    xtarot_balance_after = xtarot.balanceOf(xtarotPlugin)
    print("xtarot_balance_after", xtarot_balance_after / 1e18)
    boo_balance_after = boo.balanceOf(xtarotPlugin)
    print("boo_balance_after", boo_balance_after / 1e18)

    assert boo_balance_after > boo_balance_before


# tests that setAutoSell can't be called by anyone but the strategy and then that it works when called by gov
def test_set_auto_sell(
    accounts,
    GenericXbooXtarot,
    strategy,
    xtarot_pid,
    masterchef,
    xtarotRouter,
    xtarot,
    xtarot_swapFirstStep,
    gov,
):
    strategist = accounts[2]
    xtarotPlugin = strategist.deploy(GenericXbooXtarot, strategy, xtarot_pid, "XtarotXboo", masterchef, xtarotRouter, xtarot, xtarot_swapFirstStep, True)
    random_wallet = Contract("0x20dd72Ed959b6147912C2e529F0a0C651c33c9ce")
    
    with brownie.reverts():
        xtarotPlugin.setAutoSell(False, {'from': random_wallet})
    
    # Turn off autoSell
    xtarotPlugin.setAutoSell(False, {'from': gov})
    assert xtarotPlugin.autoSell() == False

    # Turn on autoSell
    xtarotPlugin.setAutoSell(True, {'from': gov})
    assert xtarotPlugin.autoSell() == True


# tests that setMaxSell can't be called by anyone but the strategy and then that it works when called by gov
def test_set_max_sell(
    accounts,
    GenericXbooXtarot,
    strategy,
    xtarot_pid,
    masterchef,
    xtarotRouter,
    xtarot,
    xtarot_swapFirstStep,
    gov,
):
    strategist = accounts[2]
    xtarotPlugin = strategist.deploy(GenericXbooXtarot, strategy, xtarot_pid, "XtarotXboo", masterchef, xtarotRouter, xtarot, xtarot_swapFirstStep, True)
    random_wallet = Contract("0x20dd72Ed959b6147912C2e529F0a0C651c33c9ce")
    
    with brownie.reverts():
        xtarotPlugin.setMaxSell(100, {'from': random_wallet})
    
    # Turn off autoSell
    xtarotPlugin.setMaxSell(100, {'from': gov})
    assert xtarotPlugin.maxSell() == 100


# tests that setUseSpiritOne can't be called by anyone but the strategy and then that it works when called by gov
def test_set_use_spirit_one(
    accounts,
    GenericXbooXtarot,
    strategy,
    xtarot_pid,
    masterchef,
    xtarotRouter,
    xtarot,
    xtarot_swapFirstStep,
    gov,
):
    strategist = accounts[2]
    xtarotPlugin = strategist.deploy(GenericXbooXtarot, strategy, xtarot_pid, "XtarotXboo", masterchef, xtarotRouter, xtarot, xtarot_swapFirstStep, True)
    random_wallet = Contract("0x20dd72Ed959b6147912C2e529F0a0C651c33c9ce")
    
    with brownie.reverts():
        xtarotPlugin.setUseSpiritOne(True, {'from': random_wallet})
    
    # Turn off autoSell
    xtarotPlugin.setUseSpiritOne(True, {'from': gov})
    assert xtarotPlugin.useSpiritPartOne() == True

    # Turn on autoSell
    xtarotPlugin.setUseSpiritOne(False, {'from': gov})
    assert xtarotPlugin.useSpiritPartOne() == False


# tests that setUseSpiritTwo can't be called by anyone but the strategy and then that it works when called by gov
def test_set_use_spirit_two(
    accounts,
    GenericXbooXtarot,
    strategy,
    xtarot_pid,
    masterchef,
    xtarotRouter,
    xtarot,
    xtarot_swapFirstStep,
    gov,
):
    strategist = accounts[2]
    xtarotPlugin = strategist.deploy(GenericXbooXtarot, strategy, xtarot_pid, "XtarotXboo", masterchef, xtarotRouter, xtarot, xtarot_swapFirstStep, True)
    random_wallet = Contract("0x20dd72Ed959b6147912C2e529F0a0C651c33c9ce")
    
    with brownie.reverts():
        xtarotPlugin.setUseSpiritTwo(True, {'from': random_wallet})
    
    # Turn off autoSell
    xtarotPlugin.setUseSpiritTwo(True, {'from': gov})
    assert xtarotPlugin.useSpiritPartTwo() == True

    # Turn on autoSell
    xtarotPlugin.setUseSpiritTwo(False, {'from': gov})
    assert xtarotPlugin.useSpiritPartTwo() == False