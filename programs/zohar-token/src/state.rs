use anchor_lang::prelude::*;

#[account]
pub struct TokenConfig {
    pub authority: Pubkey,
    pub treasury: Pubkey,
    pub token_price: u64,
    pub total_minted: u64,
    pub text_hash: [u8; 64],
    pub is_active: bool,
    pub bump: u8,
}

impl TokenConfig {
    pub const LEN: usize = 8 + 32 + 32 + 8 + 8 + 64 + 1 + 1;
}

#[account]
pub struct TokenRecord {
    pub owner: Pubkey,
    pub token_number: u64,
    pub text_hash: [u8; 64],
    pub minted_at: i64,
    pub bump: u8,
}

impl TokenRecord {
    pub const LEN: usize = 8 + 32 + 8 + 64 + 8 + 1;
}
