use anchor_lang::prelude::*;

#[error_code]
pub enum ZoharError {
    #[msg("LightVessel: Program is not active")]
    NotActive,
    #[msg("LightVessel: Incorrect payment amount — token price is $26 USDC")]
    IncorrectPayment,
    #[msg("LightVessel: Invalid treasury account")]
    InvalidTreasury,
    #[msg("LightVessel: Unauthorized — only DAO authority can perform this action")]
    Unauthorized,
    #[msg("LightVessel: Text hash mismatch — Zohar text integrity check failed")]
    HashMismatch,
}
