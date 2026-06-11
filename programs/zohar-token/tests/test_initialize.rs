use {
    anchor_lang::{
        prelude::Pubkey, solana_program::instruction::Instruction, system_program,
        InstructionData, ToAccountMetas,
    },
    litesvm::LiteSVM,
    solana_keypair::Keypair,
    solana_message::{Message, VersionedMessage},
    solana_signer::Signer,
    solana_transaction::versioned::VersionedTransaction,
};

#[test]
fn test_initialize() {
    let program_id = zohar_token::id();
    let payer = Keypair::new();
    let mut svm = LiteSVM::new();
    let bytes = include_bytes!("../../../target/deploy/zohar_token.so");
    svm.add_program(program_id, bytes);
    svm.airdrop(&payer.pubkey(), 1_000_000_000).unwrap();

    let treasury = Pubkey::new_unique();
    let (token_config, _bump) =
        Pubkey::find_program_address(&[zohar_token::SEED_TOKEN_CONFIG], &program_id);

    let instruction = Instruction::new_with_bytes(
        program_id,
        &zohar_token::instruction::Initialize { treasury }.data(),
        zohar_token::accounts::Initialize {
            token_config,
            authority: payer.pubkey(),
            treasury,
            system_program: system_program::ID,
        }
        .to_account_metas(None),
    );

    let blockhash = svm.latest_blockhash();
    let msg = Message::new_with_blockhash(&[instruction], Some(&payer.pubkey()), &blockhash);
    let tx = VersionedTransaction::try_new(VersionedMessage::Legacy(msg), &[payer]).unwrap();

    let res = svm.send_transaction(tx);
    assert!(res.is_ok(), "initialize failed: {:?}", res.err());
}
