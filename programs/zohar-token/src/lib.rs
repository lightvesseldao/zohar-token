pub mod constants;
pub mod error;
pub mod instructions;
pub mod state;

use anchor_lang::prelude::*;
pub use constants::*;
pub use instructions::*;
pub use state::*;

declare_id!("2i7ZBxCj5RxXpiC94F1CBCuHtFYdtYMEVSwkUTQJ4Su1");

#[program]
pub mod zohar_token {
    use super::*;

    pub fn initialize(
        ctx: Context<Initialize>,
        treasury: Pubkey,
    ) -> Result<()> {
        initialize::handler(ctx, treasury)
    }

    pub fn mint_zohar(ctx: Context<MintZohar>) -> Result<()> {
        mint_zohar::handler(ctx)
    }

    pub fn verify_ownership(ctx: Context<VerifyOwnership>) -> Result<()> {
        verify_ownership::handler(ctx)
    }
}
