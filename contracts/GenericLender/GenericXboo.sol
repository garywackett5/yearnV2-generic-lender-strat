// SPDX-License-Identifier: AGPL-3.0
// Feel free to change the license, but this is what we use

// Feel free to change this version of Solidity. We support >=0.6.0 <0.7.0;
pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;
// Gary's Generic xBOO Staker
// These are the core Yearn libraries
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/math/SafeMath.sol";
import "@openzeppelin/contracts/utils/Address.sol";
import "@openzeppelin/contracts/token/ERC20/SafeERC20.sol";
import "@openzeppelin/contracts/math/Math.sol";

import "./GenericLenderBase.sol";

// boo:xboo ratios, enter = "Locks Boo and mints xBoo", leave = "Unlocks the staked + gained Boo, and burns xBoo"
interface IXboo is IERC20 {
    function xBOOForBOO(uint256) external view returns (uint256);

    function BOOForxBOO(uint256) external view returns (uint256);

    function enter(uint256) external;

    function leave(uint256) external;
}

interface IUniswapV2Pair {
    function swap(
        uint256,
        uint256,
        address to,
        bytes calldata
    ) external;

    function getReserves()
        external
        view
        returns (
            uint256 reserve0,
            uint256 reserve1,
            uint256 timestamp
        );
}

interface IFactory {
    function getPair(address, address) external view returns (address);

    function getReserves()
        external
        view
        returns (
            uint256 reserve0,
            uint256 reserve1,
            uint256 timestamp
        );
}

interface ChefLike {
    function deposit(uint256 _pid, uint256 _amount) external;

    function withdraw(uint256 _pid, uint256 _amount) external; // use amount = 0 for harvesting rewards

    function emergencyWithdraw(uint256 _pid) external;

    function userInfo(uint256 _pid, address user) external view returns (uint256 amount, uint256 rewardDebt);

    function poolInfo(uint256 _pid)
        external
        view
        returns (
            address RewardToken,
            uint256 RewardPerSecond,
            uint256 TokenPrecision,
            uint256 xBooStakedAmount,
            uint256 lastRewardTime,
            uint256 accRewardPerShare,
            uint256 endTime,
            uint256 startTime,
            uint256 userLimitEndTime,
            address protocolOwnerAddress
        );
}

contract GenericXboo is GenericLenderBase {
    using SafeERC20 for IERC20;
    using Address for address;
    using SafeMath for uint256;

    /* ========== STATE VARIABLES ========== */

    ChefLike public masterchef;
    IERC20 public emissionToken;
    IERC20 public swapFirstStep;

    // swap stuff
    address internal constant spookyFactory = 0x152eE697f2E276fA89E96742e9bB9aB1F2E61bE3;
    address internal constant spiritFactory = 0xEF45d134b73241eDa7703fa787148D9C9F4950b0;

    // tokens
    IERC20 internal constant wftm = IERC20(0x21be370D5312f44cB42ce377BC9b8a0cEF1A4C83);
    IERC20 internal constant usdc = IERC20(0x04068DA6C83AFCFA0e13ba15A6696662335D5B75);
    IERC20 internal constant boo = IERC20(0x841FAD6EAe12c286d1Fd18d1d525DFfA75C7EFFE);
    IXboo internal constant xboo = IXboo(0xa48d959AE2E88f1dAA7D5F611E01908106dE7598);

    bool public autoSell;
    uint256 public maxSell; // set to zero for unlimited

    bool public useSpiritPartOne;
    bool public useSpiritPartTwo;

    uint256 public pid; // the pool ID we are staking for

    string internal stratName; // we use this for our strategy's name on cloning

    uint256 private constant secondsPerYear = 31_536_000;

    /* ========== CONSTRUCTOR ========== */

    constructor(
        address _strategy,
        uint256 _pid,
        string memory _name,
        address _masterchef,
        address _emissionToken,
        address _swapFirstStep,
        bool _autoSell
    ) public GenericLenderBase(_strategy, _name) {
        _initializeStrat(_pid, _masterchef, _emissionToken, _swapFirstStep, _autoSell);
    }



    // we use this to clone our original strategy to other vaults
    function cloneGenericXboo(
        address _strategy,
        uint256 _pid,
        string memory _name,
        address _masterchef,
        address _emissionToken,
        address _swapFirstStep,
        bool _autoSell
    ) external returns (address newLender) {
        newLender = _clone(_strategy, _name);
        GenericXboo(newLender).initialize(
            _pid,
            _masterchef,
            _emissionToken,
            _swapFirstStep,
            _autoSell
        );
    }

    // this will only be called by the clone function above
    function initialize(
        uint256 _pid,
        address _masterchef,
        address _emissionToken,
        address _swapFirstStep,
        bool _autoSell
    ) public {
        // _initialize(_strategy, _strategist, _rewards, _keeper);
        require(address(emissionToken) == address(0), "already initialized");
        _initializeStrat(_pid, _masterchef, _emissionToken, _swapFirstStep, _autoSell);
    }

    // this is called by our original strategy, as well as any clones
    function _initializeStrat(
        uint256 _pid,
        address _masterchef,
        address _emissionToken,
        address _swapFirstStep,
        bool _autoSell
    ) internal {
        masterchef = ChefLike(_masterchef);
        emissionToken = IERC20(_emissionToken);
        swapFirstStep = IERC20(_swapFirstStep);

        (
            address rewardsToken,
            ,
            ,
            ,
            ,
            ,
            ,
            ,
            ,
            
        ) = masterchef.poolInfo(_pid);

        require(rewardsToken == _emissionToken, "wrong token");

        autoSell = _autoSell;

        // make sure that we used the correct pid
        pid = _pid;

        // add approvals on all tokens
        want.approve(address(xboo), type(uint256).max);
        xboo.approve(address(masterchef), type(uint256).max);
    }

    /* ========== FUNCTIONS ========== */

    // balance of boo in strat - should be zero most of the time
    function balanceOfWant() public view returns (uint256) {
        return want.balanceOf(address(this));
    }

    function balanceOfXboo() public view returns (uint256) {
        return xboo.balanceOf(address(this));
    }

    // balance of xboo in strat (in boo) - should be zero most of the time
    function balanceOfXbooInWant() public view returns (uint256) {
        return xboo.xBOOForBOO(balanceOfXboo());
    }

    // balance of xboo in masterchef (in boo)
    function balanceOfStaked() public view returns (uint256) {
        (uint256 stakedInMasterchef, ) = masterchef.userInfo(pid, address(this));
        stakedInMasterchef = xboo.xBOOForBOO(stakedInMasterchef);
        return stakedInMasterchef;
    }

    // same as estimatedTotalAssets
    function nav() external view override returns (uint256) {
        return _nav();
    }

    // same as estimatedTotalAssets
    function _nav() internal view returns (uint256) {
        // look at our staked tokens and any free tokens sitting in the strategy
        return balanceOfStaked().add(balanceOfWant()).add(balanceOfXbooInWant());
    }

    function apr() external view override returns (uint256) {
        return _apr();
    }

    // calculate current reward apr
    function _apr() internal view returns (uint256) {
        return _aprAfterDeposit(0);
    }

    function aprAfterDeposit(uint256 amount) external view override returns (uint256) {
        return _aprAfterDeposit(amount);
    }

    function _aprAfterDeposit(uint256 amount) internal view returns (uint256) {
        (
            ,
            uint256 rewardsEachSecond,
            ,
            uint256 stakedXboo,
            ,
            ,
            uint256 poolEnds,
            uint256 poolStarts,
            ,
            
        ) = masterchef.poolInfo(pid);
        if (block.timestamp < poolStarts || block.timestamp > poolEnds) {
            return 0;
        }

        uint256 xbooAdded = xboo.BOOForxBOO(amount);
        uint256 booEachSecond = quoteEmissionToBoo(rewardsEachSecond.mul(10)).div(10);
        uint256 booEachYear = booEachSecond.mul(secondsPerYear);
        uint256 xbooEachYear = xboo.BOOForxBOO(booEachYear);
        uint256 newTotalXbooInPool = stakedXboo.add(xbooAdded);
        return xbooEachYear.mul(1e18).div(newTotalXbooInPool);
    }

    struct SellRoute {
        address pair;
        address input;
        address output;
        address to;
    }

    function quoteEmissionToBoo(uint256 _amount) internal view returns (uint256) {
        // we do all our sells in one go in a chain between pairs
        // inialise to 3 even if we use less to save on gas
        SellRoute[] memory sellRoute = new SellRoute[](3);

        // 1! sell our emission token for swap first step token
        address[] memory emissionTokenPath = new address[](2);
        emissionTokenPath[0] = address(emissionToken);
        emissionTokenPath[1] = address(swapFirstStep);
        uint256 id = 0;

        address factory = useSpiritPartOne ? spiritFactory : spookyFactory;
        // we deal directly with the pairs
        address pair = IFactory(factory).getPair(emissionTokenPath[0], emissionTokenPath[1]);

        // first
        sellRoute[id] = SellRoute(pair, emissionTokenPath[0], emissionTokenPath[1], address(0));

        if (address(want) == address(swapFirstStep)) {
            // end with only one step
            
            return _quoteUniswap(sellRoute, id, _amount);
        }

        // if the second token isnt wftm we need to do an etra step
        if (address(swapFirstStep) != address(wftm)) {
            id = id + 1;
            // ! 2
            emissionTokenPath[0] = address(swapFirstStep);
            emissionTokenPath[1] = address(wftm);

            pair = IFactory(spookyFactory).getPair(emissionTokenPath[0], emissionTokenPath[1]);

            // we set the to of the last step to
            sellRoute[id - 1].to = pair;

            sellRoute[id] = SellRoute(pair, emissionTokenPath[0], emissionTokenPath[1], address(0));

            if (address(want) == address(wftm)) {
                // end. final to is always us. second array
                sellRoute[id].to = address(this);

                // end with only one step
                
                return _quoteUniswap(sellRoute, id, _amount);
            }
        }

        id = id + 1;
        // final step is wftm to want
        emissionTokenPath[0] = address(wftm);
        emissionTokenPath[1] = address(want);
        factory = useSpiritPartTwo ? spiritFactory : spookyFactory;
        pair = IFactory(factory).getPair(emissionTokenPath[0], emissionTokenPath[1]);

        sellRoute[id - 1].to = pair;

        sellRoute[id] = SellRoute(pair, emissionTokenPath[0], emissionTokenPath[1], address(this));

        // id will be 0-1-2
        return _quoteUniswap(sellRoute, id, _amount);
    }

    function _quoteUniswap(
        SellRoute[] memory sell,
        uint256 id,
        uint256 amountIn
    ) internal view returns (uint256) {
        for (uint256 i = 0; i < id + 1; i++) {
            (address token0, ) = _sortTokens(sell[i].input, sell[i].output);
            IUniswapV2Pair pair = IUniswapV2Pair(sell[i].pair);

            (uint256 reserve0, uint256 reserve1, ) = pair.getReserves();
            (uint256 reserveInput, uint256 reserveOutput) = sell[i].input == token0 ? (reserve0, reserve1) : (reserve1, reserve0);

            amountIn = _getAmountOut(amountIn, reserveInput, reserveOutput);
        }

        return amountIn;
    }

    // following two functions are taken from uniswap library
    // https://github.com/Uniswap/v2-periphery/blob/master/contracts/libraries/UniswapV2Library.sol
    function _sortTokens(address tokenA, address tokenB) internal pure returns (address token0, address token1) {
        (token0, token1) = tokenA < tokenB ? (tokenA, tokenB) : (tokenB, tokenA);
    }

    function _getAmountOut(
        uint256 amountIn,
        uint256 reserveIn,
        uint256 reserveOut
    ) internal pure returns (uint256 amountOut) {
        require(amountIn > 0, "UniswapV2Library: INSUFFICIENT_INPUT_AMOUNT");
        require(reserveIn > 0 && reserveOut > 0, "UniswapV2Library: INSUFFICIENT_LIQUIDITY");
        uint256 amountInWithFee = amountIn.mul(997);
        uint256 numerator = amountInWithFee.mul(reserveOut);
        uint256 denominator = reserveIn.mul(1000).add(amountInWithFee);
        amountOut = numerator.div(denominator);
    }

    function weightedApr() external view override returns (uint256) {
        uint256 a = _apr();
        return a.mul(_nav());
    }

    function withdraw(uint256 amount) external override management returns (uint256) {
        return _withdraw(amount);
    }

    // Only do this if absolutely necessary; as assets will be withdrawn but rewards won't be claimed.
    function emergencyManualWithdraw() external management {
        masterchef.emergencyWithdraw(pid);
    }

    // Only do this if absolutely necessary; as assets will be withdrawn but rewards won't be claimed.
    function emergencyWithdraw(uint256 amount) external override management {
        masterchef.emergencyWithdraw(pid);

        // didn't have this in original xBOO HEC strat but it's there in other gen lenders
        want.safeTransfer(vault.governance(), balanceOfWant());
        IERC20(address(xboo)).safeTransfer(vault.governance(), balanceOfXboo());
    }

    // withdraw an amount including any want balance
    function _withdraw(uint256 amount) internal returns (uint256) {
        // claim our emissionToken rewards
        _claimRewards();

        // if we have emissionToken to sell, then sell all of it
         uint256 emissionTokenBalance = emissionToken.balanceOf(address(this));
        if (emissionTokenBalance > 0 && autoSell) {
            // sell our emissionToken
            _sell(emissionTokenBalance);
        }

        uint256 _liquidatedAmount;

        uint256 balanceOfBoo = balanceOfWant();
        // if we need more boo than is already loose in the contract
        if (balanceOfBoo < amount) {
            // boo needed beyond any boo that is already loose in the contract
            uint256 amountToFree = amount.sub(balanceOfBoo);
            // converts this amount into xboo
            uint256 amountToFreeInXboo = xboo.BOOForxBOO(amountToFree);
            // any xboo that is already loose in the contract
            uint256 balanceXboo = balanceOfXboo();
            // if we need more xboo than is already loose in the contract
            if (balanceXboo < amountToFreeInXboo) {
                // new amount of xboo needed after subtracting any xboo that is already loose in the contract
                uint256 newAmountToFreeInXboo = amountToFreeInXboo.sub(balanceXboo);

                (uint256 deposited, ) =
                    ChefLike(masterchef).userInfo(pid, address(this));
                // if xboo deposited in masterchef is less than what we want, deposited becomes what we want (all)
                if (deposited < newAmountToFreeInXboo) {
                    newAmountToFreeInXboo = deposited;
                }
                // stops us trying to withdraw if xboo deposited is zero
                if (deposited > 0) {
                    ChefLike(masterchef).withdraw(pid, newAmountToFreeInXboo);
                    // updating balanceOfXboo in preparation for when we leave xboo
                    balanceXboo = balanceOfXboo();
                }
            }
            // leave = "Unlocks the staked Boo + gained Boo (which should be zero?), and burns xBoo"
            // the lowest of these two options beause balanceOfXboo might be more than we need
            xboo.leave(Math.min(amountToFreeInXboo, balanceXboo));

            
            // this address' balance of boo - should it be balanceOfWant() ???
            _liquidatedAmount = want.balanceOf(address(this));
        } else {
            // shouldn't this line also be want.balanceOf(address(this))? or actually balanceOfWant()
            _liquidatedAmount = amount;
        }
        // NEW LINE
        want.safeTransfer(address(strategy), _liquidatedAmount);
        return _liquidatedAmount;
    }

    function claimRewards() external management {
        _claimRewards(); 
    }

    function _claimRewards() internal {
        // claim our emission tokens
        masterchef.withdraw(pid, 0); 
    }

    // sell from reward token to want
    function _sell(uint256 _amount) internal {

        if(maxSell > 0){
            _amount = Math.min(maxSell, _amount);
        }        

        // we do all our sells in one go in a chain between pairs
        // inialise to 3 even if we use less to save on gas
        SellRoute[] memory sellRoute = new SellRoute[](3);

        // 1! sell our emission token for swapfirststep token
        address[] memory emissionTokenPath = new address[](2);
        emissionTokenPath[0] = address(emissionToken);
        emissionTokenPath[1] = address(swapFirstStep);
        uint256 id = 0;

        address factory = useSpiritPartOne? spiritFactory: spookyFactory;
        // we deal directly with the pairs
        address pair = IFactory(factory).getPair(emissionTokenPath[0], emissionTokenPath[1]);

        // start off by sending our emission token to the first pair. we only do this once
        emissionToken.safeTransfer(pair, _amount);

        // first
        sellRoute[id] =
                SellRoute(
                    pair,
                    emissionTokenPath[0], 
                    emissionTokenPath[1],
                    address(0)
                );

        if (address(want) == address(swapFirstStep)) {

            // end with only one step
            _uniswap_sell_with_fee(sellRoute, id);
            return;
        }

        // if the second token isnt ftm we need to do an etra step
        if(address(swapFirstStep) != address(wftm)){
            id = id+1;
            // ! 2
            emissionTokenPath[0] = address(swapFirstStep);
            emissionTokenPath[1] = address(wftm);
            
            pair = IFactory(spookyFactory).getPair(emissionTokenPath[0], emissionTokenPath[1]);
            

            // we set the to of the last step to 
            sellRoute[id-1].to = pair;

            sellRoute[id] =
                SellRoute(
                    pair,
                    emissionTokenPath[0], 
                    emissionTokenPath[1],
                    address(0)
                );

            if (address(want) == address(wftm)) {

                // end with only one step
                _uniswap_sell_with_fee(sellRoute, id);
                return;
            }
        }

        id = id+1;
        // final step is wftm to want
        emissionTokenPath[0] = address(wftm);
        emissionTokenPath[1] = address(want);
        factory = useSpiritPartTwo? spiritFactory: spookyFactory;
        pair = IFactory(factory).getPair(emissionTokenPath[0], emissionTokenPath[1]);
        

        sellRoute[id - 1].to = pair;


        sellRoute[id] =
                SellRoute(
                    pair,
                    emissionTokenPath[0], 
                    emissionTokenPath[1],
                    address(this)
                );


        // id will be 0-1-2
        _uniswap_sell_with_fee(sellRoute, id);
    }

    function _uniswap_sell_with_fee(SellRoute[] memory sell, uint256 id) internal{
        sell[id].to = address(this); // last one is always to us
        for (uint i; i < id+1; i++) {
            
            (address token0,) = _sortTokens(sell[i].input, sell[i].output);
            IUniswapV2Pair pair = IUniswapV2Pair(sell[i].pair);
            uint amountInput;
            uint amountOutput;
            { // scope to avoid stack too deep errors
            (uint reserve0, uint reserve1,) = pair.getReserves();
            (uint reserveInput, uint reserveOutput) = sell[i].input == token0 ? (reserve0, reserve1) : (reserve1, reserve0);
            amountInput = IERC20(sell[i].input).balanceOf(address(pair)).sub(reserveInput);
            amountOutput = _getAmountOut(amountInput, reserveInput, reserveOutput);
            }
            (uint amount0Out, uint amount1Out) = sell[i].input == token0 ? (uint(0), amountOutput) : (amountOutput, uint(0));
            require(sell[i].to != address(0), "burning tokens");
            pair.swap(amount0Out, amount1Out, sell[i].to, new bytes(0));
        }
    }

    function deposit() external override management {
        // send all of our want tokens to be deposited
        uint256 balance = balanceOfWant();
        // stake only if we have something to stake
        if (balance > 0) {
            // deposit our boo into xboo
            xboo.enter(balance);
            // deposit xboo into masterchef
            masterchef.deposit(pid, balanceOfXboo());
        }
    }

    function withdrawAll() external override management returns (bool) {
        uint256 invested = _nav();
        // claim our emissionToken rewards
        _claimRewards();

        // if we have emissionToken to sell, then sell all of it
         uint256 emissionTokenBalance = emissionToken.balanceOf(address(this));
        if (emissionTokenBalance > 0 && autoSell) {
            // sell our emissionToken
            _sell(emissionTokenBalance);
        }
        (uint256 stakedXboo, ) = masterchef.userInfo(pid, address(this));
        if (stakedXboo > 0) {
            ChefLike(masterchef).withdraw(pid, stakedXboo);
        }

        uint256 balanceXboo = balanceOfXboo();
        xboo.leave(balanceXboo);
        uint256 balanceOfBoo = balanceOfWant();
        want.safeTransfer(address(strategy), balanceOfBoo);
    
        
        return balanceOfBoo.add(dust) >= invested;
    }

    
    function hasAssets() external view override returns (bool) {
        return _nav() > dust;
    }

    function manualSell(uint256 _amount) external management {
        _sell(_amount);
    }

    function protectedTokens()
        internal
        view
        override
        returns (address[] memory)
    {}


/* ========== SETTERS ========== */

    // autosell if pools are liquid enough
    function setAutoSell(bool _autoSell)
        external
        management
    {
        autoSell = _autoSell;
    }

    // set a max sell for illiquid pools
    function setMaxSell(uint256 _maxSell)
        external
        management
    {
        maxSell = _maxSell;
    }

    // set to use spirit instead of spooky
    function setUseSpiritOne(bool _useSpirit)
        external
        management
    {
        useSpiritPartOne = _useSpirit;
    }

    // set to use spirit instead of spooky
    function setUseSpiritTwo(bool _useSpirit)
        external
        management
    {
        useSpiritPartTwo = _useSpirit;
    }
 
}
