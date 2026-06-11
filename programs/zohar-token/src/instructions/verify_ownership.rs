use anchor_lang::prelude::*;
use crate::constants::*;
use crate::state::{TokenConfig, TokenRecord};

#[derive(Accounts)]
pub struct VerifyOwnership<'info> {
    #[account(
        seeds = [SEED_TOKEN_CONFIG],
        bump = token_config.bump
    )]
    pub token_config: Account<'info, TokenConfig>,

    #[account(
        seeds = [
            SEED_TOKEN_RECORD,
            owner.key().as_ref(),
            &token_record.token_number.checked_sub(1)
                .unwrap_or(0)
                .to_le_bytes()
        ],
        bump = token_record.bump,
        constraint = token_record.owner == owner.key()
    )]
    pub token_record: Account<'info, TokenRecord>,

    pub owner: Signer<'info>,
}

pub fn handler(ctx: Context<VerifyOwnership>) -> Result<()> {
    let record = &ctx.accounts.token_record;
    let config = &ctx.accounts.token_config;

    msg!("LightVessel — Ownership Verified");
    msg!("Owner: {}", record.owner);
    msg!("Token #: {}", record.token_number);
    msg!("Text: {}", ZOHAR_TITLE);
    msg!("Hash: {}", ZOHAR_TEXT_HASH);
    msg!("GitHub: {}", ZOHAR_GITHUB);
    msg!("Minted at: {}", record.minted_at);
    msg!("Total supply: {}", config.total_minted);

    Ok(())
}
