from itertools import count
from brownie import Wei, reverts


def test_normal_activity(
    wftm,
    boo,
    chain,
    whale,
    live_vault_new,
    live_strategy_new,
    strategy,
    GenericXboo,
    GenericXbooXtarot,
    Contract,
    accounts,
    interface,
    amount, 
    fn_isolation,
    xtarot
):
    vault = live_vault_new
    strategy = live_strategy_new
    strategist = accounts.at(strategy.strategist(), force=True)
    gov = accounts.at(vault.governance(), force=True)
    currency = boo

    starting_balance = currency.balanceOf(strategist)

    currency.approve(vault, 2 ** 256 - 1, {"from": whale})
    currency.approve(vault, 2 ** 256 - 1, {"from": strategist})

    deposit_limit = 10_000
    # vault.addStrategy(strategy, deposit_limit, 0, 2 ** 256 - 1, 1000, {"from": gov})

    whale_deposit = amount
    vault.deposit(whale_deposit, {"from": whale})
    chain.sleep(10)
    chain.mine(1)
    strategy.setWithdrawalThreshold(0, {"from": gov})

    print(whale_deposit / 1e18)
    status = strategy.lendStatuses()
    form = "{:.2%}"
    formS = "{:,.0f}"
    for j in status:
        print(
            f"Lender: {j[0]}, Deposits: {formS.format(j[1]/1e18)} APR: {form.format(j[2]/1e18)}"
        )

    strategy.harvest({"from": strategist})

    status = strategy.lendStatuses()
    form = "{:.2%}"
    formS = "{:,.0f}"
    for j in status:
        print(
            f"Lender: {j[0]}, Deposits: {formS.format(j[1]/1e18)} APR: {form.format(j[2]/1e18)}"
        )
    startingBalance = vault.totalAssets()
    strState = vault.strategies(strategy)
    startingTotalReturns = strState[7]
    for i in range(2):

        waitBlock = 25
        # print(f'\n----wait {waitBlock} blocks----')
        chain.mine(waitBlock)
        chain.sleep(waitBlock)
        # print(f'\n----harvest----')
        for j in range(strategy.numLenders()):
            lender = GenericXboo.at(strategy.lenders(j))
            navBefore = lender.nav()
            if navBefore == 0:
                continue
            # emission = interface.ERC20(lender.emissionToken())
            lender.claimRewards({'from': strategist})
            balanceOfEm = xtarot.balanceOf(lender)
            assert balanceOfEm > 0
            lender.manualSell(balanceOfEm, {'from': strategist})
            assert xtarot.balanceOf(lender) == 0
            navAfter = lender.nav()
            assert navAfter > navBefore
            print("profit: ", navAfter-navBefore)


        strategy.harvest({"from": strategist})

        # genericStateOfStrat(strategy, currency, vault)
        # genericStateOfVault(vault, currency)

        profit = (vault.totalAssets() - startingBalance) / 1e6
        strState = vault.strategies(strategy)
        totalReturns = strState[7] - startingTotalReturns
        totaleth = totalReturns / 1e6
        # print(f'Real Profit: {profit:.5f}')
        difff = profit - totaleth
        # print(f'Diff: {difff}')

        blocks_per_year = 3154 * 10**4
        assert startingBalance != 0
        time = (i + 1) * waitBlock
        assert time != 0
        apr = (totalReturns / startingBalance) * (blocks_per_year / time)
        print(totalReturns)
        print(startingBalance)

        assert apr > 0 and apr < 1
        # print(apr)
        print(f"implied apr: {apr:.8%}")

    vault.withdraw(vault.balanceOf(whale), {"from": whale})

    vBal = vault.balanceOf(strategy)
    assert vBal > 0
    
    vBefore = vault.balanceOf(strategist)
    vault.transferFrom(strategy, strategist, vBal, {"from": strategist})
    assert vault.balanceOf(strategist) - vBefore > 0


def test_debt_increment_weth(
    wftm,
    boo,
    chain,
    whale,
    vault,
    strategy,
    GenericXbooXtarot,
    accounts,
    interface,
    amount, 
    fn_isolation,
):

    strategist = accounts.at(strategy.strategist(), force=True)
    gov = accounts.at(vault.governance(), force=True)
    currency = boo

    starting_balance = currency.balanceOf(strategist)

    currency.approve(vault, 2 ** 256 - 1, {"from": whale})
    currency.approve(vault, 2 ** 256 - 1, {"from": strategist})

    deposit_limit = 10_000
    vault.addStrategy(strategy, deposit_limit, 0, 2 ** 256 - 1, 1000, {"from": gov})

    whale_deposit = amount
    vault.deposit(whale_deposit, {"from": whale})
    chain.sleep(10)
    chain.mine(1)
    strategy.setWithdrawalThreshold(0, {"from": gov})

    print(whale_deposit / 1e18)
    status = strategy.lendStatuses()
    form = "{:.2%}"
    formS = "{:,.0f}"
    for j in status:
        print(
            f"Lender: {j[0]}, Deposits: {formS.format(j[1]/1e18)} APR: {form.format(j[2]/1e18)}"
        )


    strategy.harvest({"from": strategist})

    status = strategy.lendStatuses()
    form = "{:.2%}"
    formS = "{:,.0f}"
    for j in status:
        print(
            f"Lender: {j[0]}, Deposits: {formS.format(j[1]/1e18)} APR: {form.format(j[2]/1e18)}"
        )
    startingBalance = vault.totalAssets()
    print(boo.balanceOf(whale)/1e18)
    for i in range(20):
        firstDeposit = (3000 * 1e18) / 20

        vault.deposit(firstDeposit, {"from": whale})
        print("\nDeposit: ", formS.format(firstDeposit / 1e18))
        strategy.harvest({"from": strategist})
        realApr = strategy.estimatedAPR()
        print("Current APR: ", form.format(realApr / 1e18))
        status = strategy.lendStatuses()

        for j in status:
            print(
                f"Lender: {j[0]}, Deposits: {formS.format(j[1]/1e18)}, APR: {form.format(j[2]/1e18)}"
            )

    vault.updateStrategyDebtRatio(strategy, 0, {'from': gov})
        
    t1 = strategy.harvest({"from": strategist})
    print(t1.events["Harvested"])
    vault.strategies(strategy).dict()["totalDebt"] < 10