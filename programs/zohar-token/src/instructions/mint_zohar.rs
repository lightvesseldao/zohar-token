use anchor_lang::prelude::*;
use anchor_spl::token::{self, Token, TokenAccount, Transfer};
use crate::constants::*;
use crate::state::{TokenConfig, TokenRecord};
use crate::error::ZoharError;

#[derive(Accounts)]
pub struct MintZohar<'info> {
    #[account(
        mut,
        seeds = [SEED_TOKEN_CONFIG],
        bump = token_config.bump
    )]
    pub token_config: Account<'info, TokenConfig>,

    #[account(
        init,
        payer = buyer,
        space = TokenRecord::LEN,
        seeds = [
            SEED_TOKEN_RECORD,
            buyer.key().as_ref(),
            &token_config.total_minted.to_le_bytes()
        ],
        bump
    )]
    pub token_record: Account<'info, TokenRecord>,

    #[account(mut)]
    pub buyer: Signer<'info>,

    #[account(
        mut,
        constraint = buyer_usdc.owner == buyer.key(),
    )]
    pub buyer_usdc: Account<'info, TokenAccount>,

    #[account(
        mut,
        constraint = treasury_usdc.key() == token_config.treasury
            @ ZoharError::InvalidTreasury
    )]
    pub treasury_usdc: Account<'info, TokenAccount>,

    pub token_program: Program<'info, Token>,
    pub system_program: Program<'info, System>,
}

pub fn handler(ctx: Context<MintZohar>) -> Result<()> {
    let config = &mut ctx.accounts.token_config;

    require!(config.is_active, ZoharError::NotActive);

    let transfer_ctx = CpiContext::new(
        ctx.accounts.token_program.to_account_info(),
        Transfer {
            from:      ctx.accounts.buyer_usdc.to_account_info(),
            to:        ctx.accounts.treasury_usdc.to_account_info(),
            authority: ctx.accounts.buyer.to_account_info(),
        },
    );
    token::transfer(transfer_ctx, config.token_price)?;

    let record       = &mut ctx.accounts.token_record;
    let bump         = ctx.bumps.token_record;
    let token_number = config.total_minted + 1;

    record.owner        = ctx.accounts.buyer.key();
    record.token_number = token_number;
    record.text_hash    = config.text_hash;
    record.minted_at    = Clock::get()?.unix_timestamp;
    record.bump         = bump;

    config.total_minted = token_number;

    msg!("LightVessel — Zohar Token #{} minted", token_number);
    msg!("Owner: {}", ctx.accounts.buyer.key());
    msg!("Text: {}", ZOHAR_TITLE);
    msg!("Hash: {}", ZOHAR_TEXT_HASH);
    msg!("GitHub: {}", ZOHAR_GITHUB);

    Ok(())
}
