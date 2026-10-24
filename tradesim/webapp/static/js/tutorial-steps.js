// The words of the tutorial, in order. This file is only data: tutorial.js turns each step into a card.
//
// A step has a `title` and `text` (HTML), plus any of these:
//   target  CSS selector of the part of the page to light up (none: the card sits in the middle)
//   page    the #route to show first ('board', 'trade/NVDA', …)
//   side    where the card sits next to the target: 'bottom' (default), 'top', 'left' or 'right'
//   away    extra pixels between card and target, to stay clear of a pop-up menu
//   live    leave the market clock running (otherwise it is paused when the step opens)
//   task    something the player must DO. "Next" stays locked until done(state) is true
//   after   what to show once the task is done
// Every `done` looks only at the game as it is now, so a reload can never get a player stuck.

import { store } from './store.js';

const STOCK = 'NVDA';    // the stock bought and sold in part 3

/** Shares of `symbol` the player holds. */
function held(state, symbol) {
  return state.positions.find((p) => p.s === symbol)?.qty || 0;
}

const SCREEN = [
  {
    title: '👋 Welcome to TradeSim',
    text: `<p>You have <b>$10,000</b> of pretend money and a market of <b>100 companies in 10 sectors</b>, plus 14 ETFs
        (ready-made baskets of shares). Prices are simulated but move like the real thing: good and bad moods, crashes, news,
        busy opens and closes.</p>
      <p>This tutorial has three parts:</p>
      <ol class="welcome-steps"><li><b>The screen</b>: what the top, side and bottom bars mean.</li>
        <li><b>The pages</b>: a quick visit to all ten.</li>
        <li><b>Your first game</b>: open the market, buy, sell and skip ahead, for real.</li></ol>
      <p class="muted">It takes about five minutes and can't be skipped. Everything you need is explained once, here.</p>`,
  },
  {
    target: '.clock-box',
    title: '⏱ The market clock',
    text: `<p>A trading day runs from <b>09:30 to 16:00</b>. Here it plays live: at 1× speed, <b>one second is five minutes</b> of market time.</p>
      <p><b>LIVE</b> means the market is open and <b>CLOSED</b> means the closing bell has rung. The thin bar shows how far through
      the day you are, and <b>Day 3/60</b> how far through the whole game.</p>`,
  },
  {
    target: '#index-strip',
    title: '📈 The index cards',
    text: `<p>These cards show how <b>the whole market</b> is doing: <b>MKT100</b> holds all 100 stocks, and every other card is a
      fund for one sector (tech, finance, health…). Scroll the strip to see them all.</p>
      <p>The little chart is today's path. Click a card to open its full chart.</p>`,
  },
  {
    target: '#account-chip',
    title: '💰 Your money',
    text: `<p>Your <b>total value</b>: cash plus the shares you own, at today's prices. Underneath: how much it changed
      <b>today</b> and <b>in total</b> since you started.</p><p>Click it any time to open your Portfolio.</p>`,
  },
  {
    target: '.controls',
    title: '🎛 Time controls',
    text: `<ul><li><b>▶ Open day</b> starts the clock.</li>
        <li><b>⏸ 1× 2× 5× 15×</b> pause it or make it faster (the Space bar pauses too).</li>
        <li><b>To close ⏭</b> plays the rest of the day at once.</li>
        <li><b>Skip days</b> jumps 1, 5 or 20 days, or to the end.</li></ul>
      <p>You will use every one of them in part 3.</p>`,
  },
  {
    target: '.sidenav',
    side: 'right',
    title: '🧭 Ten pages',
    text: `<p>The left menu has ten pages: <b>Board</b> (all prices), <b>Trade</b> (one symbol), <b>Portfolio</b>, <b>News</b>,
      <b>Leverage</b>, <b>Labs</b>, <b>Robo</b>, <b>Learn</b>, <b>Goals</b> and <b>Terminal</b>. We visit each one next.</p>
      <p class="muted">The <b>Tour</b> button at the bottom replays this tutorial any time.</p>`,
  },
  {
    target: '.statusbar',
    side: 'top',
    title: '📟 The status bar',
    text: `<ul><li><b>😱 Fear gauge</b>: how scared the market is, from calm through uneasy and nervous to panic. It jumps in crashes.</li>
        <li>Your <b>challenge goal</b>, or your loan if you borrow.</li>
        <li>A <b>ticker</b> with the latest headlines.</li>
        <li>The <b>seed</b>: the same seed always gives the same market, so you can replay it.</li></ul>`,
  },
];

const PAGES = [
  {
    page: 'board', target: '.board-toolbar',
    title: '📋 Board: find a stock',
    text: `<p>The <b>Board</b> lists all 100 stocks and 14 ETFs like a broker's price board, and it ticks live.</p>
      <ul><li><b>Search</b> by symbol or company name (press <b>/</b>).</li>
        <li>The tabs show your <b>★ Watchlist</b>, <b>My holdings</b>, the <b>ETFs</b>, or one sector.</li>
        <li>Click a column title (Symbol, Price, %) to <b>sort</b>.</li></ul>`,
  },
  {
    page: 'board', target: '.board thead',
    title: '🔎 Reading a row',
    text: `<ul><li><b>Ref</b> is yesterday's close. Green ▲ is above it, red ▼ below it, amber unchanged.</li>
        <li><b>Bids</b> are buyers waiting, <b>Asks</b> are sellers waiting.</li>
        <li><b>Last match</b> is the latest price with its change and %.</li>
        <li><b>Today</b>: high, low and open. <b>You</b>: the shares you own and your profit.</li></ul>`,
  },
  {
    page: 'board', target: '.board tbody tr',
    title: '⚡ Quick actions',
    text: `<ul><li><b>Double-click</b> a row for a quick order ticket (or select it and press <b>B</b> to buy, <b>S</b> to sell).</li>
        <li>Click the <b>★</b> to add it to your watchlist.</li>
        <li>Click the <b>symbol</b> to open its chart.</li></ul>`,
  },
  {
    page: `trade/${STOCK}`, target: '.quote-head',
    title: '🔍 The Trade page',
    text: `<p>One symbol in detail. Pick any other from the list at the top, or click a symbol on the Board.
      You see its <b>price</b>, the change <b>against yesterday's close</b>, and today's open, high, low and volume.</p>
      <p><b>☆ Watch</b> adds it to your watchlist.</p>`,
  },
  {
    page: `trade/${STOCK}`, target: '#page-trade .card:has(.chart-toolbar)',
    title: '📊 The candlestick chart',
    text: `<p>Each <b>candle</b> is one period: the box runs from open to close (green = closed higher, red = lower) and the thin line
      reaches the high and the low.</p>
      <ul><li><b>1D</b> shows today in 15-minute candles. <b>1M to All</b> show daily candles, with <b>120 days of history</b> from before day 0.</li>
        <li><b>MA 20 / 50</b> are moving averages: the average price of the last 20 or 50 days.</li>
        <li>Your buys and sells show up as ▲ ▼ markers.</li></ul>`,
  },
  {
    page: `trade/${STOCK}`, target: '#page-trade .card:has([data-f="ticket"])', side: 'left',
    title: '🧾 Placing an order',
    text: `<ul><li>Choose <b>Buy</b> or <b>Sell</b>, then type the number of <b>shares</b> (or tap 25% … Max). Whole shares only.</li>
        <li>These are <b>market orders</b>: they fill at once at the last price, plus a small flat fee.</li>
        <li><b>Max you can buy</b> is your buying power.</li></ul>
      <p class="muted">The order book below is for show: it lists waiting orders, but yours always fills at the last price.</p>`,
  },
  {
    page: `trade/${STOCK}`, target: '#page-trade .grid.cols-2', side: 'top',
    title: 'ℹ️ Know it before you buy it',
    text: `<ul><li><b>Beta</b> says how strongly it follows the market: above 1 it swings more, below 1 less.</li>
        <li><b>Volatility</b> is how wildly it moves over a year.</li>
        <li>🤖 The <b>Robo-analyst</b> gives the chance it is higher in 5 days. It is right only about 55% of the time!</li>
        <li>Your <b>position</b> and the latest <b>news</b> about it. For an ETF you also see the <b>holdings</b> inside.</li></ul>`,
  },
  {
    page: 'portfolio', target: '#page-portfolio .kpis',
    title: '💼 Portfolio',
    text: `<p>Your <b>total value</b>, <b>cash</b>, how much is <b>invested</b>, today's and total <b>profit or loss</b>,
      and (if you borrow) your leverage and safety cushion.</p>`,
  },
  {
    page: 'portfolio', target: '#page-portfolio .grid.cols-main-side',
    title: '🆚 You against the market',
    text: `<p>The chart compares <b>your money</b> with simply <b>buying the whole market</b> on day 0. Beating it is harder than it looks.</p>
      <p><b>Where your money sits</b> shows your mix by sector. All your eggs in one basket? That is the risk
      <b>diversification</b> fixes.</p>`,
  },
  {
    page: 'portfolio', target: '#page-portfolio .card:has([data-f="holdings"])', side: 'top',
    title: '📒 Holdings, history and Coach',
    text: `<p>Every <b>holding</b> with its average cost and profit. Further down: your full <b>trade history</b> and the
      <b>🧑‍🏫 Trade Coach</b>, which spots mistakes such as too much money in one stock or fees eating your gains.</p>`,
  },
  {
    page: 'news', target: '#page-news .card:has([data-f="list"])', side: 'right',
    title: '📰 News',
    text: `<p>Headlines hit one company, one sector or the whole market, and move prices. Each one shows how <b>Laya</b>
      (a small AI on this computer) and a <b>keyword counter</b> guessed good or bad, and after the closing bell what
      <b>really</b> happened (✔ or ✗).</p>
      <p class="muted">No news yet? Open the market: about one day in four brings a headline.</p>`,
  },
  {
    page: 'news', target: '#page-news .card:has([data-f="hl"])', side: 'left',
    title: '🗞️ Headline Lab',
    text: `<p>Write your own headline and see whether the AI and the word counter call it good or bad. Try
      <i>"Profits fall less than feared"</i>: prices move on <b>surprises</b>, so counting words often gets it wrong.</p>`,
  },
  {
    page: 'leverage', target: '#page-leverage .concepts',
    title: '⚠️ Leverage',
    text: `<p>A <b>margin account</b> lets you borrow from the broker to buy more than your cash allows. It multiplies gains
      <i>and</i> losses, the loan costs interest, and a <b>margin call</b> sells your shares for you if you lose too much.</p>
      <p>You start at <b>1× (no borrowing)</b>. Stay there while you learn.</p>`,
  },
  {
    page: 'leverage', target: '#page-leverage .grid.cols-2', side: 'top',
    title: '🎚 Leverage tools',
    text: `<ul><li>Pick <b>1× to 5×</b> to set how much the broker may lend you.</li>
        <li>The <b>calculator</b> shows what a price move does to <i>your</i> money at that leverage.</li>
        <li>Further down, the <b>Leverage Lab</b> replays this market at 1×, 2×, 3×, 5× and with a 2× fund.</li></ul>`,
  },
  {
    page: 'labs', target: '#page-labs .tabs',
    title: '🧪 Labs',
    text: `<ul><li><b>Diversification Lab</b>: one stock against a fund that holds many. See how spreading your money out smooths the ride.</li>
        <li><b>What-if Replay</b>: how your trades compare with simple strategies on this same market.</li>
        <li><b>200 markets</b>: replays an idea on 200 brand-new markets, to tell luck from skill.</li></ul>`,
  },
  {
    page: 'robo', target: '#page-robo .page-head',
    title: '🤖 Robo-analyst',
    text: `<p>Two tiny machine-learning models, written in plain Python. One guesses the market's hidden <b>mood</b>
      (bull, sideways, bear or crash), the other which prices will be <b>higher in 5 days</b>.</p>
      <p>Both were tested on markets they had never seen. The mood detector helps; the price forecaster is barely better than
      a coin flip. That is the lesson.</p>`,
  },
  {
    page: 'learn', target: '#page-learn .grid.cols-2',
    title: '🎓 Learn',
    text: `<p>A <b>quiz</b> on investing basics, <b>badges</b> you earn for milestones as you play, and below them a
      <b>glossary</b> that explains every term.</p>`,
  },
  {
    page: 'challenges', target: '#page-challenges .page-head',
    title: '🎯 Goals (challenges)',
    text: `<p>Challenges are <b>fixed markets with a story and a goal</b>, like surviving a crash. Everyone gets the same market,
      so you can compare results with classmates.</p>
      <p><b>Free play</b> at the bottom starts a new random market, or replays one from a <b>seed</b> number.</p>`,
  },
  {
    page: 'terminal', target: '#page-terminal .terminal-in', side: 'top',
    title: '⌨️ Terminal',
    text: `<p>Every button in the app just runs a typed command, and you can type them yourself. <code>help</code> lists them all.
      Try <code>quote NVDA</code>, <code>market tech</code>, <code>coach</code> or <code>whatif</code>.</p>`,
  },
];

const GAME = [
  {
    page: 'board',
    title: '🎮 Now let\'s play',
    text: `<p>You have seen everything. Now you will play a few minutes of a real game. Each step lights up what to click and waits
      until you have done it.</p>
      <ol class="welcome-steps"><li>Open the market and change its speed.</li><li>Pause, then <b>buy</b> some shares.</li>
        <li>Play the day to the close and read the summary.</li><li><b>Sell</b>, then skip a few days ahead.</li></ol>
      <p class="muted">At the end you can keep this game or start a fresh one.</p>`,
  },
  {
    page: 'board', target: '#btn-start', live: true,
    title: '▶ Open the market',
    text: '<p>Day 1 is waiting. Start the clock and watch the Board come alive.</p>',
    task: 'Click the blue <b>▶ Open day 1</b> button.',
    after: 'The market is live! Prices flash green when they tick up and red when they tick down.',
    done: (state) => state.clock.phase === 'open',
  },
  {
    target: '#speed', live: true,
    title: '🚀 Change the speed',
    text: '<p>One second per five minutes is slow. These buttons make time pass faster.</p>',
    task: 'Click <b>5×</b>.',
    after: 'Faster! At 15× a whole day takes about five seconds.',
    done: () => store.speed >= 5 && store.running,
  },
  {
    target: '#speed', live: true,
    title: '⏸ Pause',
    text: '<p>You can freeze the market any time to think, look things up or place an order. Nothing moves until you restart it.</p>',
    task: 'Click <b>⏸</b> to pause.',
    after: 'Paused. Take as long as you like.',
    done: () => !store.running,
  },
  {
    page: `trade/${STOCK}`, target: '#page-trade .card:has([data-f="ticket"])', side: 'left',
    title: '🛒 Buy your first shares',
    text: `<p>This is <b>${STOCK}</b>, a chip maker. Its order ticket is ready on the right.</p>`,
    task: 'Type <b>5</b> in <b>Shares</b> (or tap <b>25%</b>), then press the green <b>Buy</b> button.',
    after: 'Bought! Your cash went down and the shares are yours. Each trade costs a small fee, one reason not to trade too often. Look for the ▲ on the chart.',
    done: (state) => held(state, STOCK) > 0,
  },
  {
    target: '#btn-close-day',
    title: '⏭ Play the day to the close',
    text: `<p>Instead of waiting, play the rest of the day at once. A <b>closing-bell summary</b> pops up: how you did against the
      whole market, and the day's best and worst stocks. Read it, then close it with the <b>×</b>.</p>`,
    task: 'Click <b>To close ⏭</b>.',
    after: 'That was the closing bell: one trading day done.',
    done: (state) => state.clock.day >= 1,
  },
  {
    page: 'portfolio', target: '#page-portfolio .card:has([data-f="holdings"])', side: 'top',
    title: '📒 Your position',
    text: `<p>Here is your ${STOCK} position: how many shares, what you paid on average, what they are worth now and your profit
      or loss. Up or down, the lesson is the same: one stock is a gamble, a mix of many is a plan.</p>`,
  },
  {
    page: `trade/${STOCK}`, target: '#page-trade .card:has([data-f="ticket"])', side: 'left',
    title: '💵 Sell',
    text: '<p>Selling works the same way as buying. You can sell some of your shares or all of them.</p>',
    task: 'Click the red <b>Sell</b> tab, press <b>Max</b>, then press <b>Sell</b>.',
    after: 'Sold! The cash is back in your account, minus the fees. The trade is now in your history on the Portfolio page.',
    done: (state) => held(state, STOCK) === 0,
  },
  {
    target: '.menu-wrap', away: 150,
    title: '⏩ Skip ahead',
    text: `<p>A quiet stretch? Jump ahead. The market still plays out every day in between (news, crashes and all)
      and you get one summary at the end.</p>`,
    task: 'Open <b>Skip days ▾</b> and choose <b>Skip 5 days</b>.',
    after: 'Five days gone in a blink.',
    done: (state) => state.clock.day >= 2,
  },
  {
    title: '🎓 You\'re ready',
    text: `<p>That is the whole game. Three habits to take with you:</p>
      <ul><li><b>Spread your money out.</b> An ETF or several sectors beats betting on one stock.</li>
        <li><b>Don't borrow</b> until you have studied the Leverage page.</li>
        <li><b>Read the News and the Trade Coach</b>, and compare yourself with the market.</li></ul>
      <p>Your practice trades used up a few days of this game. Start again with a fresh $10,000 on a new market, or carry on from here.</p>`,
  },
];

const PARTS = [
  { name: 'The screen', steps: SCREEN },
  { name: 'The pages', steps: PAGES },
  { name: 'Your first game', steps: GAME },
];

/** All steps in one list, each labelled with its part. */
export const STEPS = PARTS.flatMap((part, i) => part.steps.map((step) => ({ ...step, part: `Part ${i + 1} · ${part.name}` })));
