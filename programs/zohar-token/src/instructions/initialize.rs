use anchor_lang::prelude::*;
use crate::constants::*;
use crate::state::TokenConfig;

#[derive(Accounts)]
pub struct Initialize<'info> {
    #[account(
        init,
        payer = authority,
        space = TokenConfig::LEN,
        seeds = [SEED_TOKEN_CONFIG],
        bump
    )]
    pub token_config: Account<'info, TokenConfig>,

    #[account(mut)]
    pub authority: Signer<'info>,

    /// CHECK: Treasury wallet — validated by authority
    pub treasury: AccountInfo<'info>,

    pub system_program: Program<'info, System>,
}

pub fn handler(ctx: Context<Initialize>, treasury: Pubkey) -> Result<()> {
    let config = &mut ctx.accounts.token_config;
    let bump = ctx.bumps.token_config;

    let mut hash_bytes = [0u8; 64];
    let bytes = ZOHAR_TEXT_HASH.as_bytes();
    hash_bytes[..bytes.len()].copy_from_slice(bytes);

    config.authority    = ctx.accounts.authority.key();
    config.treasury     = treasury;
    config.token_price  = TOKEN_PRICE_USDC;
    config.total_minted = 0;
    config.text_hash    = hash_bytes;
    config.is_active    = true;
    config.bump         = bump;

    msg!("LightVessel DAO — Zohar Token Program Initialized");
    msg!("Text Hash: {}", ZOHAR_TEXT_HASH);
    msg!("Title: {}", ZOHAR_TITLE);
    msg!("GitHub: {}", ZOHAR_GITHUB);
    msg!("Treasury: {}", treasury);

    Ok(())
}
