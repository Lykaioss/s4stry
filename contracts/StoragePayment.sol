// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract StoragePayment {
    address public owner;
    mapping(address => uint256) public balances;
    mapping(address => bool) public isRenter;
    mapping(address => bool) public isClient;
    mapping(bytes32 => StorageAgreement) public storageAgreements;
    
    struct StorageAgreement {
        address client;
        address renter;
        uint256 amount;
        uint256 startTime;
        uint256 duration;
        bool isActive;
        bool isPaid;
    }
    
    event StorageAgreementCreated(
        bytes32 agreementId,
        address client,
        address renter,
        uint256 amount,
        uint256 duration
    );
    
    event PaymentReleased(
        bytes32 agreementId,
        address client,
        address renter,
        uint256 amount
    );
    
    constructor() {
        owner = msg.sender;
    }
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this function");
        _;
    }
    
    modifier onlyRenter() {
        require(isRenter[msg.sender], "Only renters can call this function");
        _;
    }
    
    modifier onlyClient() {
        require(isClient[msg.sender], "Only clients can call this function");
        _;
    }
    
    function registerRenter() public {
        isRenter[msg.sender] = true;
    }
    
    function registerClient() public {
        isClient[msg.sender] = true;
    }
    
    function createStorageAgreement(
        address renter,
        uint256 amount,
        uint256 duration
    ) public onlyClient returns (bytes32) {
        require(isRenter[renter], "Invalid renter address");
        require(balances[msg.sender] >= amount, "Insufficient balance");
        
        bytes32 agreementId = keccak256(abi.encodePacked(
            msg.sender,
            renter,
            block.timestamp
        ));
        
        storageAgreements[agreementId] = StorageAgreement({
            client: msg.sender,
            renter: renter,
            amount: amount,
            startTime: block.timestamp,
            duration: duration,
            isActive: true,
            isPaid: false
        });
        
        // Lock the payment amount
        balances[msg.sender] -= amount;
        
        emit StorageAgreementCreated(
            agreementId,
            msg.sender,
            renter,
            amount,
            duration
        );
        
        return agreementId;
    }
    
    function releasePayment(bytes32 agreementId) public onlyClient {
        StorageAgreement storage agreement = storageAgreements[agreementId];
        require(agreement.isActive, "Agreement is not active");
        require(!agreement.isPaid, "Payment already released");
        require(agreement.client == msg.sender, "Only client can release payment");
        
        // Transfer payment to renter
        balances[agreement.renter] += agreement.amount;
        agreement.isPaid = true;
        agreement.isActive = false;
        
        emit PaymentReleased(
            agreementId,
            agreement.client,
            agreement.renter,
            agreement.amount
        );
    }
    
    function cancelAgreement(bytes32 agreementId) public {
        StorageAgreement storage agreement = storageAgreements[agreementId];
        require(agreement.isActive, "Agreement is not active");
        require(!agreement.isPaid, "Payment already released");
        require(
            msg.sender == agreement.client || msg.sender == agreement.renter,
            "Only client or renter can cancel"
        );
        
        // Return payment to client
        balances[agreement.client] += agreement.amount;
        agreement.isActive = false;
    }
    
    function getAgreement(bytes32 agreementId) public view returns (
        address client,
        address renter,
        uint256 amount,
        uint256 startTime,
        uint256 duration,
        bool isActive,
        bool isPaid
    ) {
        StorageAgreement storage agreement = storageAgreements[agreementId];
        return (
            agreement.client,
            agreement.renter,
            agreement.amount,
            agreement.startTime,
            agreement.duration,
            agreement.isActive,
            agreement.isPaid
        );
    }
    
    // Owner functions for testing
    function mintTestTokens(address account, uint256 amount) public onlyOwner {
        balances[account] += amount;
    }
} 